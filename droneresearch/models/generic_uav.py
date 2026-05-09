"""
GenericUAVModel — base UAV class with FSM + MAVLink + swarm parameters.

Based on: "A Modular and Scalable System Architecture for Heterogeneous
UAV Swarms Using ROS 2 and PX4-Autopilot" (2025)

Intended for: smaller UAVs with Raspberry Pi companion computer.
Extends:      Drone (SDK) with FSM and swarm role awareness.

Usage:
    from droneresearch.models import GenericUAVModel

    uav = GenericUAVModel("D1", "tcp:127.0.0.1:5760")
    uav.connect()
    uav.start()          # arms + takes off based on FSM
    uav.set_role("follower", leader_id="D1")
"""
import math
import threading
import time
from typing import Optional

from droneresearch.core.fsm import DroneState, StateMachine
from droneresearch.sdk.drone import Drone


class GenericUAVModel(Drone):
    """
    Base UAV model with Finite State Machine and swarm parameter store.

    Swarm roles:
        "none"      — standalone, no swarm
        "leader"    — leads formation, others follow
        "follower"  — follows a designated leader
        "coordinator" — manages the swarm (see CoordinatorUAVModel)
    """

    def __init__(
        self,
        drone_id:          str,
        connection_string: str,
        log_dir:           str  = "logs",
        auto_log:          bool = True,
    ):
        super().__init__(
            connection_string,
            drone_id=drone_id,
            log_dir=log_dir,
            auto_log=auto_log,
        )
        # FSM
        self.fsm = StateMachine(drone_id=drone_id)
        self.fsm.on_transition(self._on_fsm_transition)

        # Swarm parameters
        self.swarm_role:      str           = "none"
        self.leader_id:       Optional[str] = None
        self.formation_offset: tuple        = (0.0, 0.0, 0.0)   # (north_m, east_m, alt_m)
        self.swarm_id:        Optional[str] = None

        # Wire MAVLink events → FSM
        self.on("armed",  self._sync_armed)
        self.on("mode",   self._sync_mode)

        self._mission_thread: Optional[threading.Thread] = None

    # ── FSM-driven operations ─────────────────────────────────────────────

    def start(self, altitude: float = 10.0, timeout: float = 60.0) -> bool:
        """FSM-driven arm + takeoff sequence."""
        if not self.fsm.transition(DroneState.ARMING):
            print(f"[{self.id}] FSM: cannot arm from {self.fsm.state.name}")
            return False
        time.sleep(1.0)   # brief pause to let SITL EKF stabilize
        ok = self.arm(timeout=20.0)
        if not ok:
            self.fsm.transition(DroneState.IDLE)
            return False
        self.fsm.transition(DroneState.ARMED)
        if not self.fsm.transition(DroneState.TAKEOFF):
            return False
        ok = self.takeoff(altitude=altitude, timeout=max(timeout, 30.0))
        if not ok:
            # Takeoff timed out but drone may still be airborne — force FLYING
            if self.altitude > altitude * 0.5:
                self.fsm.transition(DroneState.FLYING)
                return True
            self.fsm.emergency()
            return False
        self.fsm.transition(DroneState.FLYING)
        return True

    def stop(self, force: bool = False) -> bool:
        """FSM-driven land sequence."""
        if self.fsm.is_airborne:
            self.fsm.transition(DroneState.LANDING, force=force)
            ok = self.land()
            if ok:
                self.fsm.transition(DroneState.IDLE)
            return ok
        return True

    def return_home(self) -> bool:
        if not self.fsm.is_airborne:
            return False
        self.fsm.transition(DroneState.RTL, force=True)
        self.rtl()
        return True

    def run_mission_fsm(self, waypoints: list, timeout: float = 600.0) -> bool:
        """FSM-aware waypoint navigation using goto (no mission protocol)."""
        if self.fsm.state not in (DroneState.FLYING, DroneState.MISSION):
            print(f"[{self.id}] FSM: must be FLYING to start mission, is {self.fsm.state.name}")
            return False
        self.fsm.transition(DroneState.MISSION, force=True)
        try:
            for wp in waypoints:
                lat = wp["lat"] if isinstance(wp, dict) else wp.lat
                lon = wp["lon"] if isinstance(wp, dict) else wp.lon
                alt = wp.get("alt", self.altitude) if isinstance(wp, dict) else wp.alt
                self._conn.set_mode("GUIDED")
                self._conn.goto(lat, lon, alt)
                # Warte bis nah genug am Waypoint (max 60s pro WP)
                deadline = time.time() + 60.0
                while time.time() < deadline:
                    try:
                        dlat = (self.lat - lat) * 111320.0
                        dlon = (self.lon - lon) * 111320.0 * math.cos(math.radians(lat))
                        if math.sqrt(dlat**2 + dlon**2) < 3.0:
                            break
                    except Exception:
                        pass
                    time.sleep(0.5)
        finally:
            self.fsm.transition(DroneState.FLYING, force=True)
        return True

    # ── Swarm role ────────────────────────────────────────────────────────

    def set_role(self, role: str, leader_id: Optional[str] = None):
        """Set swarm role. role = 'none' | 'leader' | 'follower' | 'coordinator'"""
        self.swarm_role = role
        self.leader_id  = leader_id

    def set_formation_offset(self, north_m: float, east_m: float, alt_m: float = 0.0):
        """Set offset from leader position in NED meters."""
        self.formation_offset = (north_m, east_m, alt_m)

    # ── Status ────────────────────────────────────────────────────────────

    def status(self) -> dict:
        t = self.telemetry
        return {
            "id":       self.id,
            "state":    self.fsm.state.name,
            "role":     self.swarm_role,
            "leader":   self.leader_id,
            "armed":    t.armed,
            "mode":     t.flight_mode,
            "lat":      t.lat,
            "lon":      t.lon,
            "alt":      t.alt_rel,
            "battery":  t.battery_pct,
            "gps_fix":  t.gps_fix,
        }

    # ── FSM sync from MAVLink telemetry ───────────────────────────────────

    def _sync_armed(self, armed: bool):
        """Sync FSM when MAVLink armed state changes."""
        if armed and self.fsm.state == DroneState.ARMING:
            self.fsm.transition(DroneState.ARMED)
        elif not armed:
            # Ignore armed=false during ARMING/TAKEOFF/FLYING — those states handle
            # their own transitions; only land/disarm should trigger IDLE
            if self.fsm.state in (DroneState.LANDING, DroneState.RTL):
                if self.altitude < 1.0:
                    self.fsm.transition(DroneState.IDLE, force=True)

    def _sync_mode(self, mode: str):
        """Sync FSM on mode change."""
        mode = mode.upper()
        if mode == "RTL" and self.fsm.is_airborne:
            self.fsm.transition(DroneState.RTL, force=True)
        elif mode == "LAND" and self.fsm.is_airborne:
            self.fsm.transition(DroneState.LANDING, force=True)
        elif mode == "AUTO" and self.fsm.state == DroneState.FLYING:
            self.fsm.transition(DroneState.MISSION)

    def _on_fsm_transition(self, old: DroneState, new: DroneState):
        print(f"[{self.id}] {old.name} → {new.name}")
        if new == DroneState.EMERGENCY:
            self._handle_emergency()

    def _handle_emergency(self):
        print(f"[{self.id}] EMERGENCY — sending RTL")
        self.rtl()

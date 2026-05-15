"""
FSM — Finite State Machine for drone operations.

Based on: "A Modular and Scalable System Architecture for Heterogeneous
UAV Swarms Using ROS 2 and PX4-Autopilot" (2025)

States:
    IDLE       — connected, disarmed, on ground
    ARMING     — arm command sent, waiting for confirmation
    ARMED      — armed, on ground
    TAKEOFF    — takeoff in progress
    FLYING     — airborne, in LOITER/GUIDED
    MISSION    — executing autonomous mission
    RTL        — returning to launch
    LANDING    — landing in progress
    EMERGENCY  — failsafe / emergency
    ERROR      — unrecoverable error

Valid transitions:
    IDLE      → ARMING
    ARMING    → ARMED | IDLE (arm failed)
    ARMED     → TAKEOFF | IDLE (disarmed)
    TAKEOFF   → FLYING | EMERGENCY
    FLYING    → MISSION | RTL | LANDING | EMERGENCY
    MISSION   → FLYING | RTL | EMERGENCY
    RTL       → LANDING | EMERGENCY
    LANDING   → IDLE | EMERGENCY
    EMERGENCY → IDLE (manual reset only)
    ERROR     → IDLE (manual reset only)
"""
import threading
import time
from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Set, Tuple


class DroneState(Enum):
    IDLE      = auto()
    ARMING    = auto()
    ARMED     = auto()
    TAKEOFF   = auto()
    FLYING    = auto()
    MISSION   = auto()
    RTL       = auto()
    LANDING   = auto()
    EMERGENCY = auto()
    ERROR     = auto()


# Valid transitions: state → set of reachable states
_TRANSITIONS: Dict[DroneState, Set[DroneState]] = {
    DroneState.IDLE:      {DroneState.ARMING},
    DroneState.ARMING:    {DroneState.ARMED, DroneState.IDLE},
    DroneState.ARMED:     {DroneState.TAKEOFF, DroneState.IDLE},
    DroneState.TAKEOFF:   {DroneState.FLYING, DroneState.EMERGENCY},
    DroneState.FLYING:    {DroneState.MISSION, DroneState.RTL, DroneState.LANDING, DroneState.EMERGENCY},
    DroneState.MISSION:   {DroneState.FLYING, DroneState.RTL, DroneState.EMERGENCY},
    DroneState.RTL:       {DroneState.LANDING, DroneState.EMERGENCY},
    DroneState.LANDING:   {DroneState.IDLE, DroneState.EMERGENCY},
    DroneState.EMERGENCY: {DroneState.IDLE},
    DroneState.ERROR:     {DroneState.IDLE},
}

# State groups for convenience checks
AIRBORNE_STATES = {DroneState.TAKEOFF, DroneState.FLYING, DroneState.MISSION, DroneState.RTL, DroneState.LANDING}
SAFE_STATES     = {DroneState.IDLE, DroneState.ARMED}


class StateMachine:
    """
    Thread-safe drone FSM.

    Usage:
        fsm = StateMachine(drone_id="D1")
        fsm.on_transition(lambda old, new: print(f"{old} → {new}"))
        fsm.transition(DroneState.ARMING)
    """

    def __init__(self, drone_id: str = "drone"):
        self.drone_id   = drone_id
        self._state     = DroneState.IDLE
        self._prev      = DroneState.IDLE
        self._lock      = threading.Lock()
        self._history:  List[Tuple[float, DroneState, DroneState]] = []
        self._callbacks: List[Callable[[DroneState, DroneState], None]] = []
        self._reject_callbacks: List[Callable[[DroneState, DroneState], None]] = []
        self._rejected: int = 0

    @property
    def state(self) -> DroneState:
        return self._state

    @property
    def previous(self) -> DroneState:
        return self._prev

    @property
    def is_airborne(self) -> bool:
        return self._state in AIRBORNE_STATES

    @property
    def is_safe(self) -> bool:
        return self._state in SAFE_STATES

    @property
    def can_arm(self) -> bool:
        return self._state == DroneState.IDLE

    @property
    def can_takeoff(self) -> bool:
        return self._state == DroneState.ARMED

    @property
    def can_mission(self) -> bool:
        return self._state == DroneState.FLYING

    def transition(self, new_state: DroneState, force: bool = False) -> bool:
        """
        Attempt to transition to new_state.
        Returns True if successful, False if transition not allowed.
        Set force=True to bypass validation (emergency use only).

        Rejected transitions are counted, logged once with the offending
        (current_state, requested_state) pair and dispatched to any
        callbacks registered via :meth:`on_rejection` so the UI can show
        a warning without polling.
        """
        with self._lock:
            allowed = _TRANSITIONS.get(self._state, set())
            current = self._state
            if not force and new_state not in allowed:
                self._rejected += 1
                rejected_from = current
            else:
                rejected_from = None
                old = self._state
                self._prev  = old
                self._state = new_state
                self._history.append((time.time(), old, new_state))
                if len(self._history) > 500:
                    self._history = self._history[-500:]
        # Outside lock
        if rejected_from is not None:
            print(
                f"[fsm:{self.drone_id}] REJECTED {rejected_from.name} \u2192 {new_state.name} "
                f"(allowed: {sorted(s.name for s in _TRANSITIONS.get(rejected_from, set()))})"
            )
            for cb in self._reject_callbacks:
                try:
                    cb(rejected_from, new_state)
                except Exception as e:
                    print(f"[fsm:{self.drone_id}] reject-callback error: {e}")
            return False
        for cb in self._callbacks:
            try:
                cb(old, new_state)
            except Exception as e:
                print(f"[fsm:{self.drone_id}] callback error: {e}")
        return True

    def on_transition(self, cb: Callable[[DroneState, DroneState], None]):
        """Register callback fired on every state transition."""
        self._callbacks.append(cb)

    def on_rejection(self, cb: Callable[[DroneState, DroneState], None]):
        """Register callback fired when an invalid transition is rejected.

        Signature: ``cb(current_state, requested_state)``.
        """
        self._reject_callbacks.append(cb)

    @property
    def rejected_count(self) -> int:
        return self._rejected

    def reset(self):
        """Force reset to IDLE (emergency/manual)."""
        self.transition(DroneState.IDLE, force=True)

    def emergency(self):
        """Immediate transition to EMERGENCY (always allowed)."""
        self.transition(DroneState.EMERGENCY, force=True)

    def history(self, last_n: int = 20) -> List[dict]:
        with self._lock:
            entries = self._history[-last_n:]
        return [
            {"t": round(t, 2), "from": old.name, "to": new.name}
            for t, old, new in entries
        ]

    def __repr__(self) -> str:
        return f"StateMachine({self.drone_id}: {self._state.name})"

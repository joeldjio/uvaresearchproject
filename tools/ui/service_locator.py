"""
ServiceLocator — minimal dependency-injection container for the GCS.

Replaces the pile of manual signal-connections in `app.py` with a tiny
registry that owns every long-lived service (contexts, models) and
provides one place to wire them up.

Design goals
------------
* No magic. Services are plain QObjects, registered by string key.
* Lazy: services can be registered as a factory and only instantiated
  on first .get() call. Saves cold-start time.
* Single wire-up step: `wire(locator)` mutates the locator with all
  the cross-context signal connections.
* Easy to mock for tests: `locator.register("swarm", FakeSwarm())`.

Usage
-----
    locator = ServiceLocator()
    locator.register_factory("swarm",      lambda: SwarmContext())
    locator.register_factory("telemetry",  lambda: TelemetryModel())
    ...
    locator.eager_init()    # instantiate all
    wire(locator)            # connect signals
    for name, obj in locator.items():
        qml_ctx.setContextProperty(name, obj)
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Iterator, Optional, Tuple


class ServiceLocator:
    """Tiny DI container: register, get, iterate."""

    def __init__(self) -> None:
        self._instances: Dict[str, Any] = {}
        self._factories: Dict[str, Callable[[], Any]] = {}

    # ── Registration ─────────────────────────────────────────────────
    def register(self, key: str, instance: Any) -> None:
        """Register an already-constructed service."""
        self._instances[key] = instance

    def register_factory(self, key: str, factory: Callable[[], Any]) -> None:
        """Register a zero-arg factory; instantiated on first .get()."""
        self._factories[key] = factory

    # ── Lookup ───────────────────────────────────────────────────────
    def get(self, key: str) -> Any:
        if key in self._instances:
            return self._instances[key]
        if key in self._factories:
            inst = self._factories[key]()
            self._instances[key] = inst
            return inst
        raise KeyError(f"ServiceLocator: '{key}' not registered")

    def has(self, key: str) -> bool:
        return key in self._instances or key in self._factories

    # ── Bulk operations ──────────────────────────────────────────────
    def eager_init(self) -> None:
        """Instantiate every registered factory now."""
        for key in list(self._factories.keys()):
            if key not in self._instances:
                self._instances[key] = self._factories[key]()

    def items(self) -> Iterator[Tuple[str, Any]]:
        """Yield (key, instance) for every constructed service."""
        return iter(self._instances.items())

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def __contains__(self, key: str) -> bool:
        return self.has(key)


def build_default_locator() -> ServiceLocator:
    """
    Factory-style construction: every context is registered as a
    factory so that imports stay deferred until eager_init() runs.
    """
    loc = ServiceLocator()

    def _swarm():
        from tools.ui.context.swarm_context import SwarmContext
        return SwarmContext()

    def _telemetry():
        from tools.ui.context.telemetry_context import TelemetryModel
        return TelemetryModel()

    def _experiment():
        from tools.ui.context.experiment_context import ExperimentContext
        return ExperimentContext()

    def _safety():
        from tools.ui.context.safety_context import SafetyContext
        return SafetyContext()

    def _ros2():
        from tools.ui.context.ros2_context import ROS2Context
        return ROS2Context()

    def _updater():
        from tools.ui.updater import UpdaterContext
        return UpdaterContext()

    def _license():
        from tools.ui.license import LicenseManager
        return LicenseManager()

    loc.register_factory("swarm",          _swarm)
    loc.register_factory("telemetryModel", _telemetry)
    loc.register_factory("experiment",     _experiment)
    loc.register_factory("safety",         _safety)
    loc.register_factory("ros2",           _ros2)
    loc.register_factory("updater",        _updater)
    loc.register_factory("licenseManager", _license)
    return loc


def wire(locator: ServiceLocator) -> None:
    """
    Connect cross-context signals. Idempotent — safe to call once.
    All connections previously living in `app.py:run()` live here now.
    """
    swarm      = locator["swarm"]
    tele_model = locator["telemetryModel"]
    experiment = locator["experiment"]
    safety     = locator["safety"]
    ros2       = locator["ros2"]

    # Telemetry → models
    swarm.telemetryUpdated.connect(
        lambda snap: tele_model.update_all(snap) if isinstance(snap, dict) else None
    )
    swarm.telemetryUpdated.connect(safety.updateDronePositions)

    # Drone count change notifications
    swarm.droneAdded.connect(lambda _: swarm.countsChanged.emit())
    swarm.droneRemoved.connect(lambda _: swarm.countsChanged.emit())

    # Auto-APF when more than 1 drone connected
    def _check_auto_apf(_drone_id: str = "") -> None:
        connected = sum(
            1 for b in swarm.backend.all_backends().values() if b.is_connected
        )
        if connected > 1 and not safety.apfActive:
            safety.configureAPF({})
            swarm.logMessage.emit(
                "INFO", "[SAFETY] APF automatisch aktiviert (>1 Drone verbunden)"
            )
        elif connected <= 1 and safety.apfActive:
            safety.disableAPF()
            swarm.logMessage.emit("INFO", "[SAFETY] APF deaktiviert (nur 1 Drone)")

    swarm.connectedChanged.connect(lambda _id, _ok: _check_auto_apf(_id))

    # Experiment logs → swarm log
    experiment.logMessage.connect(
        lambda text: swarm.logMessage.emit("INFO", f"[EXP] {text}")
    )
    experiment.scriptLogMessage.connect(
        lambda text: swarm.logMessage.emit("INFO", f"[EXP] {text}")
    )

    # Safety logs → swarm log
    safety.logMessage.connect(swarm.logMessage)
    safety.apfLogMessage.connect(
        lambda text: swarm.logMessage.emit(
            "ERROR" if "VIOLATION" in text or "ERROR" in text
            else "WARN" if "WARN" in text
            else "INFO",
            f"[SAFETY] {text}",
        )
    )
    safety.geofenceBreached.connect(
        lambda did, reason: swarm.logMessage.emit(
            "ERROR", f"[{did}] 🚨 GEOFENCE BREACH: {reason}"
        )
    )

    # Active collision avoidance: when APF detects an imminent collision, push
    # the "mover" drone to a safe waypoint via the swarm goto API.
    def _on_avoidance(drone_id: str, lat: float, lon: float, alt: float) -> None:
        try:
            b = swarm.backend.get_backend(drone_id)
            if not b or not hasattr(b, "goto"):
                return
            # Never override an active mission — the drone is already
            # executing a waypoint plan; an APF push would derail it.
            mission_active = getattr(swarm, "_mission_active", set())
            if drone_id in mission_active:
                return
            # Skip if the drone is currently following a Leader-Follower
            # formation (the formation update loop owns the goto commands).
            if (getattr(swarm, "_swarm_algorithms_active", False)
                    and getattr(swarm, "_leader_follower_enabled", False)
                    and drone_id != getattr(swarm, "_leader_drone_id", "")):
                return
            # Only push armed/airborne drones — pushing an unarmed drone is a no-op
            snap = b.get_telemetry_snapshot() if hasattr(b, "get_telemetry_snapshot") else {}
            if not (snap and snap.get("armed", False) and snap.get("alt_rel", 0.0) > 0.5):
                return
            b.goto(lat, lon, alt)
            swarm.logMessage.emit(
                "WARN",
                f"[SAFETY] APF auto-avoidance: pushing {drone_id} → "
                f"{lat:.5f}, {lon:.5f} @ {alt:.1f}m",
            )
        except Exception as exc:
            swarm.logMessage.emit("ERROR", f"[SAFETY] auto-avoidance failed: {exc}")

    safety.avoidanceTriggered.connect(_on_avoidance)

    # ROS2 logs → swarm log
    ros2.ros2LogMessage.connect(swarm.logMessage)

"""
Tests for tools.ui.service_locator.wire() — cross-context signal routing.

We don't construct the real Swarm/Safety/Experiment contexts (they pull
MAVLink, threading and Qt timers). Instead, we register tiny QObject
fakes that expose exactly the signals + slots that ``wire()`` touches.
This isolates the routing logic and runs fast.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QObject, Signal, Slot, Property

from tools.ui.service_locator import ServiceLocator, wire


# ── Fake contexts ───────────────────────────────────────────────────────────


class _FakeBackend:
    def __init__(self):
        self._all = {}

    def all_backends(self):
        return dict(self._all)

    def get_backend(self, drone_id):
        return self._all.get(drone_id)


class FakeDroneBackend:
    """Stand-in for DroneBackend with the attrs wire() checks on avoidance."""

    def __init__(self, *, connected=True, armed=True, alt_rel=10.0):
        self.is_connected = connected
        self._snap = {"armed": armed, "alt_rel": alt_rel}
        self.goto_calls: list = []

    def get_telemetry_snapshot(self):
        return dict(self._snap)

    def goto(self, lat, lon, alt):
        self.goto_calls.append((lat, lon, alt))


class FakeSwarm(QObject):
    telemetryUpdated  = Signal("QVariant")
    droneAdded        = Signal(str)
    droneRemoved      = Signal(str)
    countsChanged     = Signal()
    connectedChanged  = Signal(str, bool)
    logMessage        = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.backend = _FakeBackend()
        self._mission_active: set = set()
        self._swarm_algorithms_active = False
        self._leader_follower_enabled = False
        self._leader_drone_id = ""


class FakeTelemetryModel(QObject):
    def __init__(self):
        super().__init__()
        self.update_all_calls: list = []

    def update_all(self, snap):
        self.update_all_calls.append(snap)


class FakeSafety(QObject):
    logMessage          = Signal(str, str)
    apfLogMessage       = Signal(str)
    geofenceBreached    = Signal(str, str)
    avoidanceTriggered  = Signal(str, float, float, float)
    apfActiveChanged    = Signal()

    def __init__(self):
        super().__init__()
        self._apf_active = False
        self.configured_with: list = []
        self.disable_calls = 0
        self.position_updates: list = []

    @Property(bool, notify=apfActiveChanged)
    def apfActive(self):
        return self._apf_active

    @Slot("QVariant")
    def configureAPF(self, params=None):
        self.configured_with.append(params)
        self._apf_active = True
        self.apfActiveChanged.emit()

    @Slot()
    def disableAPF(self):
        self.disable_calls += 1
        self._apf_active = False
        self.apfActiveChanged.emit()

    @Slot("QVariant")
    def updateDronePositions(self, snap):
        self.position_updates.append(snap)


class FakeExperiment(QObject):
    logMessage       = Signal(str)
    scriptLogMessage = Signal(str)


class FakeROS2(QObject):
    ros2LogMessage = Signal(str, str)


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def wired_locator(qapp):
    """Locator pre-populated with fakes and run through wire()."""
    from tools.ui.context.bag_playback_context import BagPlaybackContext
    
    loc = ServiceLocator()
    loc.register("swarm",          FakeSwarm())
    loc.register("telemetryModel", FakeTelemetryModel())
    loc.register("experiment",     FakeExperiment())
    loc.register("safety",         FakeSafety())
    loc.register("ros2",           FakeROS2())
    loc.register("bagPlayback",    BagPlaybackContext())  # Add missing service
    wire(loc)
    return loc


# ── Telemetry routing ───────────────────────────────────────────────────────


def test_telemetry_signal_updates_model(wired_locator):
    swarm = wired_locator["swarm"]
    model = wired_locator["telemetryModel"]
    snap = {"D1": {"lat": 1.0}}
    swarm.telemetryUpdated.emit(snap)
    assert model.update_all_calls == [snap]


def test_telemetry_signal_also_pushed_to_safety(wired_locator):
    swarm  = wired_locator["swarm"]
    safety = wired_locator["safety"]
    snap = {"D1": {"lat": 1.0}}
    swarm.telemetryUpdated.emit(snap)
    assert safety.position_updates == [snap]


def test_non_dict_telemetry_payload_does_not_crash_model(wired_locator):
    """Defensive check inside wire(): non-dict payload is dropped."""
    swarm = wired_locator["swarm"]
    model = wired_locator["telemetryModel"]
    swarm.telemetryUpdated.emit("not-a-dict")
    assert model.update_all_calls == []


# ── Drone count notifications ───────────────────────────────────────────────


def test_drone_add_remove_emits_counts_changed(wired_locator):
    swarm = wired_locator["swarm"]
    fired = []
    swarm.countsChanged.connect(lambda: fired.append(True))
    swarm.droneAdded.emit("D1")
    swarm.droneRemoved.emit("D1")
    assert fired == [True, True]


# ── Auto-APF on connected drone count ───────────────────────────────────────


def test_auto_apf_enables_when_more_than_one_drone_connected(wired_locator):
    swarm  = wired_locator["swarm"]
    safety = wired_locator["safety"]

    swarm.backend._all = {
        "D1": FakeDroneBackend(connected=True),
        "D2": FakeDroneBackend(connected=True),
    }
    assert not safety.apfActive
    swarm.connectedChanged.emit("D2", True)
    assert safety.apfActive
    assert safety.configured_with  # configureAPF called


def test_auto_apf_disables_when_only_one_drone_remains(wired_locator):
    swarm  = wired_locator["swarm"]
    safety = wired_locator["safety"]

    # Start with APF on
    safety.configureAPF({})
    assert safety.apfActive

    swarm.backend._all = {"D1": FakeDroneBackend(connected=True)}
    swarm.connectedChanged.emit("D1", True)

    assert not safety.apfActive
    assert safety.disable_calls == 1


def test_auto_apf_no_change_with_zero_connected(wired_locator):
    swarm  = wired_locator["swarm"]
    safety = wired_locator["safety"]
    swarm.backend._all = {}
    swarm.connectedChanged.emit("X", False)
    assert not safety.apfActive
    assert safety.disable_calls == 0


# ── Log forwarding ──────────────────────────────────────────────────────────


def test_experiment_log_is_forwarded_to_swarm_log(wired_locator):
    swarm  = wired_locator["swarm"]
    exp    = wired_locator["experiment"]
    seen   = []
    swarm.logMessage.connect(lambda lvl, text: seen.append((lvl, text)))

    exp.logMessage.emit("scenario started")
    exp.scriptLogMessage.emit("print output")

    assert ("INFO", "[EXP] scenario started") in seen
    assert ("INFO", "[EXP] print output")    in seen


def test_safety_apf_log_classifies_violation_as_error(wired_locator):
    swarm  = wired_locator["swarm"]
    safety = wired_locator["safety"]
    seen   = []
    swarm.logMessage.connect(lambda lvl, text: seen.append((lvl, text)))

    safety.apfLogMessage.emit("VIOLATION: D1↔D2 distance 0.4m")
    safety.apfLogMessage.emit("WARN: getting close")
    safety.apfLogMessage.emit("monitor started")

    levels = [lvl for lvl, _ in seen]
    assert "ERROR" in levels
    assert "WARN"  in levels
    assert "INFO"  in levels


def test_geofence_breach_logs_as_error(wired_locator):
    swarm  = wired_locator["swarm"]
    safety = wired_locator["safety"]
    seen   = []
    swarm.logMessage.connect(lambda lvl, text: seen.append((lvl, text)))

    safety.geofenceBreached.emit("D1", "radius exceeded")
    assert seen
    lvl, text = seen[0]
    assert lvl == "ERROR"
    assert "D1" in text and "radius exceeded" in text


def test_safety_log_message_is_forwarded_directly(wired_locator):
    swarm  = wired_locator["swarm"]
    safety = wired_locator["safety"]
    seen   = []
    swarm.logMessage.connect(lambda lvl, text: seen.append((lvl, text)))

    safety.logMessage.emit("WARN", "battery low")
    assert ("WARN", "battery low") in seen


def test_ros2_log_is_forwarded_to_swarm_log(wired_locator):
    swarm = wired_locator["swarm"]
    ros2  = wired_locator["ros2"]
    seen  = []
    swarm.logMessage.connect(lambda lvl, text: seen.append((lvl, text)))

    ros2.ros2LogMessage.emit("INFO", "bridge up")
    assert ("INFO", "bridge up") in seen


# ── APF auto-avoidance ──────────────────────────────────────────────────────


def test_avoidance_triggers_goto_on_target_drone(wired_locator):
    swarm  = wired_locator["swarm"]
    safety = wired_locator["safety"]

    drone = FakeDroneBackend(armed=True, alt_rel=10.0)
    swarm.backend._all = {"D1": drone}

    safety.avoidanceTriggered.emit("D1", 47.1, 8.1, 12.0)

    assert drone.goto_calls == [(47.1, 8.1, 12.0)]


def test_avoidance_skipped_for_unarmed_drone(wired_locator):
    swarm  = wired_locator["swarm"]
    safety = wired_locator["safety"]

    drone = FakeDroneBackend(armed=False, alt_rel=10.0)
    swarm.backend._all = {"D1": drone}
    safety.avoidanceTriggered.emit("D1", 0, 0, 0)
    assert drone.goto_calls == []


def test_avoidance_skipped_when_on_ground(wired_locator):
    """A drone with alt_rel <= 0.5m is considered grounded — no push."""
    swarm  = wired_locator["swarm"]
    safety = wired_locator["safety"]

    drone = FakeDroneBackend(armed=True, alt_rel=0.2)
    swarm.backend._all = {"D1": drone}
    safety.avoidanceTriggered.emit("D1", 0, 0, 0)
    assert drone.goto_calls == []


def test_avoidance_skipped_during_active_mission(wired_locator):
    swarm  = wired_locator["swarm"]
    safety = wired_locator["safety"]

    drone = FakeDroneBackend(armed=True, alt_rel=10.0)
    swarm.backend._all = {"D1": drone}
    swarm._mission_active.add("D1")

    safety.avoidanceTriggered.emit("D1", 47.1, 8.1, 12.0)
    assert drone.goto_calls == []


def test_avoidance_skipped_for_follower_in_formation(wired_locator):
    swarm  = wired_locator["swarm"]
    safety = wired_locator["safety"]

    leader   = FakeDroneBackend(armed=True, alt_rel=10.0)
    follower = FakeDroneBackend(armed=True, alt_rel=10.0)
    swarm.backend._all = {"L": leader, "F": follower}
    swarm._swarm_algorithms_active  = True
    swarm._leader_follower_enabled  = True
    swarm._leader_drone_id          = "L"

    safety.avoidanceTriggered.emit("F", 47.1, 8.1, 12.0)
    assert follower.goto_calls == []

    # The leader itself still receives avoidance pushes
    safety.avoidanceTriggered.emit("L", 47.2, 8.2, 12.0)
    assert leader.goto_calls == [(47.2, 8.2, 12.0)]


def test_avoidance_no_crash_on_unknown_drone(wired_locator):
    """Avoidance for a drone that doesn't exist must be silently ignored."""
    swarm  = wired_locator["swarm"]
    safety = wired_locator["safety"]
    swarm.backend._all = {}
    # Should not raise
    safety.avoidanceTriggered.emit("GHOST", 0.0, 0.0, 0.0)

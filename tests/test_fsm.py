"""Tests for :mod:`droneresearch.core.fsm`."""
from __future__ import annotations

import threading

import pytest

from droneresearch.core.fsm import (
    AIRBORNE_STATES,
    SAFE_STATES,
    DroneState,
    StateMachine,
)


class TestValidTransitions:
    def test_initial_state_is_idle(self):
        fsm = StateMachine("d1")
        assert fsm.state == DroneState.IDLE
        assert fsm.previous == DroneState.IDLE
        assert fsm.is_safe
        assert not fsm.is_airborne

    def test_happy_path_idle_to_flying(self):
        fsm = StateMachine("d1")
        assert fsm.transition(DroneState.ARMING)
        assert fsm.transition(DroneState.ARMED)
        assert fsm.transition(DroneState.TAKEOFF)
        assert fsm.transition(DroneState.FLYING)
        assert fsm.state == DroneState.FLYING
        assert fsm.is_airborne
        assert fsm.rejected_count == 0

    def test_can_helpers_match_state(self):
        fsm = StateMachine("d1")
        assert fsm.can_arm
        assert not fsm.can_takeoff
        fsm.transition(DroneState.ARMING)
        fsm.transition(DroneState.ARMED)
        assert fsm.can_takeoff
        assert not fsm.can_arm

    def test_history_records_transitions(self):
        fsm = StateMachine("d1")
        fsm.transition(DroneState.ARMING)
        fsm.transition(DroneState.IDLE)
        hist = fsm.history()
        assert len(hist) == 2
        assert hist[0]["from"] == "IDLE" and hist[0]["to"] == "ARMING"
        assert hist[1]["from"] == "ARMING" and hist[1]["to"] == "IDLE"


class TestInvalidTransitions:
    def test_rejected_transition_does_not_change_state(self):
        fsm = StateMachine("d1")
        # ARMING -> MISSION is invalid (must go IDLE/ARMED first).
        fsm.transition(DroneState.ARMING)
        assert not fsm.transition(DroneState.MISSION)
        assert fsm.state == DroneState.ARMING
        assert fsm.rejected_count == 1

    def test_rejection_callback_receives_pair(self):
        fsm = StateMachine("d1")
        seen: list = []
        fsm.on_rejection(lambda cur, req: seen.append((cur, req)))
        fsm.transition(DroneState.ARMING)
        fsm.transition(DroneState.MISSION)        # invalid
        fsm.transition(DroneState.FLYING)         # invalid
        assert seen == [
            (DroneState.ARMING, DroneState.MISSION),
            (DroneState.ARMING, DroneState.FLYING),
        ]
        assert fsm.rejected_count == 2

    def test_force_bypasses_validation(self):
        fsm = StateMachine("d1")
        fsm.transition(DroneState.ARMING)
        assert fsm.transition(DroneState.MISSION, force=True)
        assert fsm.state == DroneState.MISSION
        assert fsm.rejected_count == 0  # forced calls don't count


class TestSpecialOperations:
    def test_emergency_from_any_state(self):
        for start in (DroneState.IDLE, DroneState.FLYING, DroneState.MISSION):
            fsm = StateMachine("d1")
            fsm.transition(start, force=True)
            fsm.emergency()
            assert fsm.state == DroneState.EMERGENCY

    def test_reset_returns_to_idle(self):
        fsm = StateMachine("d1")
        fsm.transition(DroneState.ARMING)
        fsm.reset()
        assert fsm.state == DroneState.IDLE

    def test_callback_exception_does_not_break_fsm(self):
        fsm = StateMachine("d1")
        fsm.on_transition(lambda old, new: 1 / 0)
        # Should still transition despite the broken callback.
        assert fsm.transition(DroneState.ARMING)
        assert fsm.state == DroneState.ARMING


class TestStateGroups:
    @pytest.mark.parametrize("state", list(AIRBORNE_STATES))
    def test_airborne_states_report_airborne(self, state):
        fsm = StateMachine("d1")
        fsm.transition(state, force=True)
        assert fsm.is_airborne
        assert not fsm.is_safe

    @pytest.mark.parametrize("state", list(SAFE_STATES))
    def test_safe_states_report_safe(self, state):
        fsm = StateMachine("d1")
        fsm.transition(state, force=True)
        assert fsm.is_safe
        assert not fsm.is_airborne


class TestThreadSafety:
    def test_concurrent_transitions_dont_corrupt_state(self):
        """50 threads hammering on transition() should leave the FSM in a
        consistent state and count rejections correctly."""
        fsm = StateMachine("d1")
        fsm.transition(DroneState.ARMING)  # park in a state with two allowed exits

        N = 50
        start_barrier = threading.Barrier(N)

        def worker():
            start_barrier.wait()
            # Each worker tries an invalid transition.
            fsm.transition(DroneState.MISSION)

        threads = [threading.Thread(target=worker) for _ in range(N)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert fsm.state == DroneState.ARMING            # never moved
        assert fsm.rejected_count == N                   # every attempt counted

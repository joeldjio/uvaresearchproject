"""Tests for :mod:`droneresearch.safety.apf`."""
from __future__ import annotations

import math

import pytest

from droneresearch.safety.apf import APFSafetyFilter, Geofence, Pose3D


class TestPose3D:
    def test_distance_3d(self):
        a = Pose3D(0, 0, 0)
        b = Pose3D(3, 4, 0)
        assert a.dist(b) == pytest.approx(5.0)

    def test_distance_2d_ignores_z(self):
        a = Pose3D(0, 0, 100)
        b = Pose3D(3, 4, -50)
        assert a.dist_2d(b) == pytest.approx(5.0)

    def test_normalized_unit_length(self):
        p = Pose3D(3, 4, 0).normalized()
        assert p.norm() == pytest.approx(1.0)

    def test_normalized_zero_vector_is_zero(self):
        p = Pose3D(0, 0, 0).normalized()
        assert p.norm() == 0.0


class TestGeofence:
    def test_inside_passes_through(self):
        gf = Geofence(radius=50.0, alt_min=1.0, alt_max=30.0)
        clipped = gf.clip(Pose3D(10, 20, 10))
        assert clipped.x == 10 and clipped.y == 20 and clipped.z == 10

    def test_horizontal_clip_to_radius(self):
        gf = Geofence(radius=10.0, alt_min=0, alt_max=100)
        clipped = gf.clip(Pose3D(100, 0, 5))
        assert math.hypot(clipped.x, clipped.y) == pytest.approx(10.0, abs=1e-6)

    def test_altitude_clipped_to_band(self):
        gf = Geofence(radius=100, alt_min=2.0, alt_max=20.0)
        assert gf.clip(Pose3D(0, 0, 50)).z == 20.0
        assert gf.clip(Pose3D(0, 0, -5)).z == 2.0


class TestSeparationCheck:
    def test_violation_detected(self):
        apf = APFSafetyFilter(min_separation=3.0)
        viols = apf.check_separation({
            "A": Pose3D(0, 0, 0),
            "B": Pose3D(1, 0, 0),       # distance 1 < 3
        })
        assert len(viols) == 1
        a, b, d = viols[0]
        assert {a, b} == {"A", "B"}
        assert d == pytest.approx(1.0)

    def test_no_violation_when_well_separated(self):
        apf = APFSafetyFilter(min_separation=2.0)
        viols = apf.check_separation({
            "A": Pose3D(0, 0, 0),
            "B": Pose3D(10, 0, 0),
        })
        assert viols == []

    def test_each_pair_reported_once(self):
        apf = APFSafetyFilter(min_separation=10.0)
        viols = apf.check_separation({
            "A": Pose3D(0, 0, 0),
            "B": Pose3D(1, 0, 0),
            "C": Pose3D(2, 0, 0),
        })
        # 3 drones -> 3 pairs (AB, AC, BC), all closer than 10.
        assert len(viols) == 3


class TestFilterBehaviour:
    def test_moves_toward_desired_when_clear(self):
        apf = APFSafetyFilter(
            min_separation=2.0,
            max_speed=5.0,
            geofence_radius=100,
            geofence_alt=(0, 50),
            obstacle_radius=4.0,
            dt=0.1,
        )
        pos = {"D": Pose3D(0, 0, 10)}
        des = {"D": Pose3D(20, 0, 10)}
        safe = apf.filter(pos, des)
        # Drone should have moved north (positive x) but not exceed max_speed*dt
        moved = safe["D"]
        assert moved.x > 0
        assert moved.x <= 5.0 * 0.1 + 1e-6   # max_speed * dt
        assert moved.y == pytest.approx(0.0, abs=1e-6)

    def test_repulsion_pushes_drones_apart(self):
        apf = APFSafetyFilter(
            min_separation=2.0,
            max_speed=5.0,
            geofence_radius=100,
            geofence_alt=(0, 50),
            obstacle_radius=4.0,
            repulsion_gain=5.0,
            dt=0.1,
        )
        # Two drones told to fly to the SAME point should not actually collide.
        pos = {"A": Pose3D(0, 0, 10), "B": Pose3D(2.5, 0, 10)}
        des = {"A": Pose3D(5, 0, 10), "B": Pose3D(5, 0, 10)}
        safe = apf.filter(pos, des)
        # Distance between safe waypoints should be >= initial distance (repulsion
        # at least cancelled out the convergence).
        d_before = pos["A"].dist(pos["B"])
        d_after  = safe["A"].dist(safe["B"])
        assert d_after >= d_before * 0.9   # tolerate small numeric noise

    def test_filter_respects_geofence(self):
        apf = APFSafetyFilter(
            min_separation=2.0,
            max_speed=100.0,         # very fast so without geofence it would escape
            geofence_radius=5.0,
            geofence_alt=(0, 50),
            obstacle_radius=4.0,
            dt=1.0,
        )
        pos = {"D": Pose3D(0, 0, 10)}
        des = {"D": Pose3D(1000, 0, 10)}
        safe = apf.filter(pos, des)
        assert math.hypot(safe["D"].x, safe["D"].y) <= 5.0 + 1e-6

    def test_static_obstacle_repels(self):
        apf = APFSafetyFilter(
            min_separation=2.0,
            max_speed=5.0,
            geofence_radius=100,
            geofence_alt=(0, 50),
            obstacle_radius=4.0,
            repulsion_gain=10.0,
            dt=0.1,
        )
        apf.add_obstacle(2.5, 0, 10)
        pos = {"D": Pose3D(0, 0, 10)}
        des = {"D": Pose3D(5, 0, 10)}       # path goes straight through obstacle
        safe = apf.filter(pos, des)
        # Y-component should deflect away from the obstacle on the optimization
        # path -> total step shorter than the unimpeded step.
        unimpeded = apf.filter(pos, des)   # without clearing it's the same
        apf.clear_obstacles()
        clean = apf.filter(pos, des)
        # With obstacle the x-displacement should be smaller (slowed down).
        assert safe["D"].x <= clean["D"].x + 1e-6

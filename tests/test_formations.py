"""Tests for :mod:`droneresearch.sdk.formations` and its consumers."""
from __future__ import annotations

import math

import pytest

from droneresearch.sdk.formations import SHAPES, formation_offsets


class TestEdgeCases:
    @pytest.mark.parametrize("count,spacing", [(0, 5), (-1, 5), (3, 0), (3, -2)])
    def test_invalid_inputs_return_empty(self, count, spacing):
        assert formation_offsets("line", count, spacing) == []

    def test_unknown_shape_falls_back_to_line(self):
        result = formation_offsets("nonsense", 3, 5.0)
        # Line: followers trail straight behind, east=0.
        assert all(e == 0.0 for _, e in result)
        assert [n for n, _ in result] == [-5.0, -10.0, -15.0]


class TestLineShape:
    def test_followers_trail_behind_leader(self):
        offs = formation_offsets("line", 4, 5.0)
        assert offs == [(-5.0, 0.0), (-10.0, 0.0), (-15.0, 0.0), (-20.0, 0.0)]


class TestVShape:
    def test_v_uses_proper_60_degree_geometry(self):
        # 60° V => cos30=0.866, sin30=0.5
        offs = formation_offsets("v", 2, 10.0)
        n0, e0 = offs[0]
        n1, e1 = offs[1]
        # First follower on left side (negative east).
        assert n0 == pytest.approx(-10 * math.cos(math.radians(30)), abs=1e-6)
        assert e0 == pytest.approx(-10 * math.sin(math.radians(30)), abs=1e-6)
        # Second follower symmetric on right side.
        assert n1 == n0
        assert e1 == pytest.approx(-e0, abs=1e-6)

    def test_v_alias_normalizes_to_canonical(self):
        a = formation_offsets("v-shape", 2, 5.0)
        b = formation_offsets("v", 2, 5.0)
        c = formation_offsets("V-Shape", 2, 5.0)
        assert a == b == c

    def test_v_followers_increase_rank_in_pairs(self):
        offs = formation_offsets("v", 4, 10.0)
        # Pairs (0,1) at rank 1, pairs (2,3) at rank 2 -> further north.
        assert offs[0][0] == offs[1][0]                     # same rank
        assert offs[2][0] == offs[3][0]                     # same rank
        assert abs(offs[2][0]) > abs(offs[0][0])            # rank 2 further behind


class TestCircleShape:
    def test_circle_points_on_ring(self):
        offs = formation_offsets("circle", 4, 5.0)
        radius = 5.0 * 4 / (2 * math.pi)
        for n, e in offs:
            r = math.hypot(n, e)
            assert r == pytest.approx(radius, abs=1e-6)


class TestGridShape:
    def test_grid_count_matches_requested(self):
        for n in (1, 4, 9, 16):
            assert len(formation_offsets("grid", n, 2.0)) == n

    def test_grid_offsets_are_unique(self):
        # No two followers should occupy the same slot.
        offs = formation_offsets("grid", 12, 3.0)
        assert len(set(offs)) == len(offs)

    def test_grid_only_trails_behind_or_at_leader_row(self):
        # Grid lays out behind the leader (negative north) plus the leader's
        # own row. Followers never fly ahead of the leader.
        for n, _ in formation_offsets("grid", 12, 3.0):
            assert n <= 0


class TestWedge:
    def test_wedge_alternates_sides(self):
        offs = formation_offsets("wedge", 4, 10.0)
        # Sides alternate (east sign flips); north always negative.
        east_signs = [1 if e > 0 else -1 for _, e in offs]
        assert east_signs == [-1, 1, -1, 1]
        assert all(n < 0 for n, _ in offs)


class TestShapesContract:
    """All canonical shapes must obey basic invariants."""

    @pytest.mark.parametrize("shape", SHAPES)
    def test_returns_correct_count(self, shape):
        assert len(formation_offsets(shape, 5, 4.0)) == 5

    @pytest.mark.parametrize("shape", SHAPES)
    def test_returns_tuples_of_two_floats(self, shape):
        for off in formation_offsets(shape, 3, 4.0):
            assert isinstance(off, tuple)
            assert len(off) == 2
            assert all(isinstance(x, float) for x in off)


class TestConsumersDelegate:
    """The SDK SwarmAPI and CoordinatorUAV must call into the canonical
    function rather than re-implement geometry."""

    def test_swarm_api_uses_canonical(self):
        from droneresearch.sdk.swarm_api import Swarm
        # Swarm._calc_offsets(count_incl_leader=4, ...) ==
        # canonical formation_offsets("v", 3, ...).
        api_result = Swarm._calc_offsets("v", 4, 5.0)
        canonical = formation_offsets("v", 3, 5.0)
        assert api_result == canonical

    def test_coordinator_uav_uses_canonical(self):
        from droneresearch.models.coordinator_uav import _calc_offsets
        assert _calc_offsets("line", 3, 5.0) == formation_offsets("line", 3, 5.0)

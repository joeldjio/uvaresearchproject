"""
Tests for multi-drone field coverage distribution strategies.
"""

from __future__ import annotations

import pytest

from droneresearch.control.field_coverage import (
    FieldCoveragePlanner,
    FieldBoundary,
    CoverageConfig,
    CoveragePattern,
    MultiDroneStrategy,
)


@pytest.fixture
def planner():
    """Create planner with home position set."""
    p = FieldCoveragePlanner()
    p.set_home_position(47.397742, 8.545594)
    return p


@pytest.fixture
def simple_boundary():
    """Simple rectangular field boundary."""
    return FieldBoundary([
        (47.397742, 8.545594),  # SW corner
        (47.398742, 8.545594),  # NW corner
        (47.398742, 8.546594),  # NE corner
        (47.397742, 8.546594),  # SE corner
    ])


@pytest.fixture
def coverage_config():
    """Standard coverage configuration."""
    return CoverageConfig(
        pattern=CoveragePattern.PARALLEL_LINES,
        altitude=20.0,
        line_spacing=10.0,
        overlap=0.2,
        speed=5.0
    )


def test_single_drone_strategy(planner, simple_boundary, coverage_config):
    """Test SINGLE_DRONE strategy returns all waypoints to one drone."""
    waypoints = planner.generate_coverage_waypoints(simple_boundary, coverage_config)
    
    distributed = planner.distribute_waypoints_for_swarm(
        waypoints, num_drones=3, strategy=MultiDroneStrategy.SINGLE_DRONE
    )
    
    assert len(distributed) == 1
    assert "D1" in distributed
    assert len(distributed["D1"]) == len(waypoints)


def test_offset_pattern_distribution(planner, simple_boundary, coverage_config):
    """Test OFFSET_PATTERN distributes waypoints in round-robin fashion."""
    waypoints = planner.generate_coverage_waypoints(simple_boundary, coverage_config)
    
    distributed = planner.distribute_waypoints_for_swarm(
        waypoints, num_drones=3, strategy=MultiDroneStrategy.OFFSET_PATTERN
    )
    
    assert len(distributed) == 3
    assert "D1" in distributed
    assert "D2" in distributed
    assert "D3" in distributed
    
    # Total waypoints should match
    total = sum(len(wps) for wps in distributed.values())
    assert total == len(waypoints)
    
    # Each drone should have roughly equal waypoints (±1)
    counts = [len(wps) for wps in distributed.values()]
    assert max(counts) - min(counts) <= 1


def test_sequential_apf_strategy(planner, simple_boundary, coverage_config):
    """Test SEQUENTIAL_APF gives same waypoints to all drones."""
    waypoints = planner.generate_coverage_waypoints(simple_boundary, coverage_config)
    
    distributed = planner.distribute_waypoints_for_swarm(
        waypoints, num_drones=3, strategy=MultiDroneStrategy.SEQUENTIAL_APF
    )
    
    assert len(distributed) == 3
    
    # All drones get same waypoints
    for drone_id in ["D1", "D2", "D3"]:
        assert len(distributed[drone_id]) == len(waypoints)


def test_formation_flight_strategy(planner, simple_boundary, coverage_config):
    """Test FORMATION_FLIGHT creates offset waypoints for followers."""
    waypoints = planner.generate_coverage_waypoints(simple_boundary, coverage_config)
    
    distributed = planner.distribute_waypoints_for_swarm(
        waypoints, num_drones=3, strategy=MultiDroneStrategy.FORMATION_FLIGHT,
        formation_offset=5.0
    )
    
    assert len(distributed) == 3
    
    # Leader gets original waypoints
    assert len(distributed["D1"]) == len(waypoints)
    
    # Followers get same number of waypoints but offset
    assert len(distributed["D2"]) == len(waypoints)
    assert len(distributed["D3"]) == len(waypoints)
    
    # Follower waypoints should be different from leader
    assert distributed["D2"][0] != distributed["D1"][0]
    assert distributed["D3"][0] != distributed["D1"][0]


def test_field_splitting_zones(planner, simple_boundary, coverage_config):
    """Test field splitting creates separate zones for each drone."""
    zones = planner.split_field_into_zones(simple_boundary, num_zones=3, config=coverage_config)
    
    assert len(zones) == 3
    assert "D1" in zones
    assert "D2" in zones
    assert "D3" in zones
    
    # Each zone should have waypoints
    for drone_id, waypoints in zones.items():
        assert len(waypoints) > 0
        # Each waypoint should be (lat, lon, alt)
        for wp in waypoints:
            assert len(wp) == 3
            lat, lon, alt = wp
            assert isinstance(lat, float)
            assert isinstance(lon, float)
            assert alt == coverage_config.altitude


def test_field_splitting_single_zone(planner, simple_boundary, coverage_config):
    """Test field splitting with single zone returns full field."""
    zones = planner.split_field_into_zones(simple_boundary, num_zones=1, config=coverage_config)
    
    assert len(zones) == 1
    assert "D1" in zones
    
    # Should match full field coverage
    full_coverage = planner.generate_coverage_waypoints(simple_boundary, coverage_config)
    assert len(zones["D1"]) == len(full_coverage)


def test_offset_pattern_with_two_drones(planner, simple_boundary, coverage_config):
    """Test offset pattern with 2 drones splits waypoints evenly."""
    waypoints = planner.generate_coverage_waypoints(simple_boundary, coverage_config)
    
    distributed = planner.distribute_waypoints_for_swarm(
        waypoints, num_drones=2, strategy=MultiDroneStrategy.OFFSET_PATTERN
    )
    
    assert len(distributed) == 2
    
    # With 2 drones, waypoints should be split almost evenly
    d1_count = len(distributed["D1"])
    d2_count = len(distributed["D2"])
    assert abs(d1_count - d2_count) <= 1
    assert d1_count + d2_count == len(waypoints)


def test_formation_offset_parameter(planner, simple_boundary, coverage_config):
    """Test formation offset parameter affects follower positions."""
    waypoints = planner.generate_coverage_waypoints(simple_boundary, coverage_config)
    
    # Small offset
    dist_small = planner.distribute_waypoints_for_swarm(
        waypoints, num_drones=2, strategy=MultiDroneStrategy.FORMATION_FLIGHT,
        formation_offset=3.0
    )
    
    # Large offset
    dist_large = planner.distribute_waypoints_for_swarm(
        waypoints, num_drones=2, strategy=MultiDroneStrategy.FORMATION_FLIGHT,
        formation_offset=10.0
    )
    
    # Leader waypoints should be identical
    assert dist_small["D1"] == dist_large["D1"]
    
    # Follower waypoints should differ based on offset
    assert dist_small["D2"] != dist_large["D2"]


def test_invalid_num_drones(planner, simple_boundary, coverage_config):
    """Test error handling for invalid number of drones."""
    waypoints = planner.generate_coverage_waypoints(simple_boundary, coverage_config)
    
    with pytest.raises(ValueError, match="Number of drones must be positive"):
        planner.distribute_waypoints_for_swarm(
            waypoints, num_drones=0, strategy=MultiDroneStrategy.OFFSET_PATTERN
        )
    
    with pytest.raises(ValueError, match="Number of drones must be positive"):
        planner.distribute_waypoints_for_swarm(
            waypoints, num_drones=-1, strategy=MultiDroneStrategy.OFFSET_PATTERN
        )


def test_field_splitting_invalid_zones(planner, simple_boundary, coverage_config):
    """Test error handling for invalid number of zones."""
    with pytest.raises(ValueError, match="Number of zones must be positive"):
        planner.split_field_into_zones(simple_boundary, num_zones=0, config=coverage_config)
    
    with pytest.raises(ValueError, match="Number of zones must be positive"):
        planner.split_field_into_zones(simple_boundary, num_zones=-1, config=coverage_config)


def test_formation_without_home_position():
    """Test formation flight requires home position."""
    planner = FieldCoveragePlanner()
    # Don't set home position
    
    boundary = FieldBoundary([
        (47.397742, 8.545594),
        (47.398742, 8.545594),
        (47.398742, 8.546594),
        (47.397742, 8.546594),
    ])
    
    config = CoverageConfig()
    
    # Can't generate waypoints without home
    with pytest.raises(ValueError, match="Home position must be set"):
        planner.generate_coverage_waypoints(boundary, config)

# Made with Bob

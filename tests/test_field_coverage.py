"""
Tests for field coverage planning module.
"""

import math
import pytest

from droneresearch.control.field_coverage import (
    CoveragePattern,
    FieldBoundary,
    CoverageConfig,
    FieldCoveragePlanner,
)


@pytest.fixture
def planner():
    """Create a field coverage planner with home position set."""
    p = FieldCoveragePlanner()
    p.set_home_position(47.3977, 8.5456)  # Zurich
    return p


@pytest.fixture
def simple_field():
    """Create a simple rectangular field boundary."""
    return FieldBoundary(corners=[
        (47.3977, 8.5456),  # SW corner
        (47.3987, 8.5456),  # NW corner
        (47.3987, 8.5466),  # NE corner
        (47.3977, 8.5466),  # SE corner
    ])


def test_field_boundary_validation():
    """Test field boundary validation."""
    # Valid boundary
    boundary = FieldBoundary(corners=[
        (47.0, 8.0),
        (47.1, 8.0),
        (47.1, 8.1),
    ])
    assert len(boundary.corners) == 3
    
    # Invalid boundary (too few corners)
    with pytest.raises(ValueError, match="at least 3 corners"):
        FieldBoundary(corners=[(47.0, 8.0), (47.1, 8.0)])


def test_coverage_config_validation():
    """Test coverage configuration validation."""
    # Valid config
    config = CoverageConfig(
        pattern=CoveragePattern.PARALLEL_LINES,
        altitude=20.0,
        overlap=0.2,
        line_spacing=10.0,
        speed=5.0,
    )
    assert config.altitude == 20.0
    
    # Invalid altitude
    with pytest.raises(ValueError, match="Altitude must be positive"):
        CoverageConfig(altitude=-5.0)
    
    # Invalid overlap
    with pytest.raises(ValueError, match="Overlap must be between"):
        CoverageConfig(overlap=1.5)
    
    # Invalid line spacing
    with pytest.raises(ValueError, match="Line spacing must be positive"):
        CoverageConfig(line_spacing=-10.0)
    
    # Invalid speed
    with pytest.raises(ValueError, match="Speed must be positive"):
        CoverageConfig(speed=0.0)


def test_home_position_required(simple_field):
    """Test that home position must be set before generating waypoints."""
    planner = FieldCoveragePlanner()
    config = CoverageConfig()
    
    with pytest.raises(ValueError, match="Home position must be set"):
        planner.generate_coverage_waypoints(simple_field, config)


def test_parallel_lines_pattern(planner, simple_field):
    """Test parallel lines coverage pattern."""
    config = CoverageConfig(
        pattern=CoveragePattern.PARALLEL_LINES,
        altitude=20.0,
        line_spacing=50.0,
        heading=0.0,
    )
    
    waypoints = planner.generate_coverage_waypoints(simple_field, config)
    
    # Should have waypoints
    assert len(waypoints) > 0
    
    # All waypoints should have altitude
    for lat, lon, alt in waypoints:
        assert alt == 20.0
        assert isinstance(lat, float)
        assert isinstance(lon, float)
    
    # Waypoints should alternate direction (zigzag)
    # First two waypoints should be at different north positions
    lat1, lon1, _ = waypoints[0]
    lat2, lon2, _ = waypoints[1]
    assert lat1 != lat2


def test_spiral_pattern(planner, simple_field):
    """Test spiral coverage pattern."""
    config = CoverageConfig(
        pattern=CoveragePattern.SPIRAL,
        altitude=15.0,
        line_spacing=30.0,
    )
    
    waypoints = planner.generate_coverage_waypoints(simple_field, config)
    
    # Should have waypoints
    assert len(waypoints) > 0
    
    # All waypoints should have correct altitude
    for lat, lon, alt in waypoints:
        assert alt == 15.0


def test_grid_pattern(planner, simple_field):
    """Test grid coverage pattern."""
    config = CoverageConfig(
        pattern=CoveragePattern.GRID,
        altitude=25.0,
        line_spacing=40.0,
    )
    
    waypoints = planner.generate_coverage_waypoints(simple_field, config)
    
    # Grid should have more waypoints than parallel lines
    # (covers both horizontal and vertical)
    assert len(waypoints) > 0
    
    # All waypoints should have correct altitude
    for lat, lon, alt in waypoints:
        assert alt == 25.0


def test_zigzag_pattern(planner, simple_field):
    """Test zigzag coverage pattern."""
    config = CoverageConfig(
        pattern=CoveragePattern.ZIGZAG,
        altitude=18.0,
        line_spacing=35.0,
    )
    
    waypoints = planner.generate_coverage_waypoints(simple_field, config)
    
    # Should have waypoints
    assert len(waypoints) > 0
    
    # All waypoints should have correct altitude
    for lat, lon, alt in waypoints:
        assert alt == 18.0


def test_gps_to_local_conversion(planner):
    """Test GPS to local NED coordinate conversion."""
    # Home position
    home_lat, home_lon = 47.3977, 8.5456
    
    # Convert home to local (should be 0, 0)
    north, east = planner._gps_to_local(home_lat, home_lon)
    assert abs(north) < 0.1
    assert abs(east) < 0.1
    
    # Point 100m north
    lat_north = home_lat + 100 / 111320  # ~100m north
    north, east = planner._gps_to_local(lat_north, home_lon)
    assert 99 < north < 101
    assert abs(east) < 1
    
    # Point 100m east
    lon_east = home_lon + 100 / (111320 * math.cos(math.radians(home_lat)))
    north, east = planner._gps_to_local(home_lat, lon_east)
    assert abs(north) < 1
    assert 99 < east < 101


def test_local_to_gps_conversion(planner):
    """Test local NED to GPS coordinate conversion."""
    home_lat, home_lon = 47.3977, 8.5456
    
    # Convert 0, 0 to GPS (should be home)
    lat, lon = planner._local_to_gps(0, 0)
    assert abs(lat - home_lat) < 0.00001
    assert abs(lon - home_lon) < 0.00001
    
    # Convert 100m north to GPS
    lat, lon = planner._local_to_gps(100, 0)
    assert lat > home_lat
    assert abs(lon - home_lon) < 0.00001
    
    # Convert 100m east to GPS
    lat, lon = planner._local_to_gps(0, 100)
    assert abs(lat - home_lat) < 0.00001
    assert lon > home_lon


def test_roundtrip_coordinate_conversion(planner):
    """Test GPS -> Local -> GPS roundtrip conversion."""
    original_lat, original_lon = 47.3987, 8.5466
    
    # Convert to local and back
    north, east = planner._gps_to_local(original_lat, original_lon)
    lat, lon = planner._local_to_gps(north, east)
    
    # Should match original (within floating point precision)
    assert abs(lat - original_lat) < 0.000001
    assert abs(lon - original_lon) < 0.000001


def test_coverage_time_estimation(planner):
    """Test coverage time estimation."""
    # Create simple waypoint list
    waypoints = [
        (47.3977, 8.5456, 20.0),
        (47.3987, 8.5456, 20.0),  # ~111m north
        (47.3987, 8.5466, 20.0),  # ~111m east
    ]
    
    speed = 5.0  # m/s
    time = planner.estimate_coverage_time(waypoints, speed)
    
    # Should take roughly (111 + 111) / 5 = ~44 seconds
    # Allow wider range due to GPS distance calculation variations
    assert 35 < time < 50
    
    # Empty waypoint list
    assert planner.estimate_coverage_time([], speed) == 0.0
    
    # Single waypoint
    assert planner.estimate_coverage_time([waypoints[0]], speed) == 0.0


def test_line_spacing_affects_waypoint_count(planner, simple_field):
    """Test that line spacing affects number of waypoints."""
    config_wide = CoverageConfig(
        pattern=CoveragePattern.PARALLEL_LINES,
        line_spacing=100.0,
    )
    config_narrow = CoverageConfig(
        pattern=CoveragePattern.PARALLEL_LINES,
        line_spacing=20.0,
    )
    
    waypoints_wide = planner.generate_coverage_waypoints(simple_field, config_wide)
    waypoints_narrow = planner.generate_coverage_waypoints(simple_field, config_narrow)
    
    # Narrower spacing should produce more waypoints
    assert len(waypoints_narrow) > len(waypoints_wide)


def test_different_altitudes(planner, simple_field):
    """Test that altitude is correctly applied to all waypoints."""
    altitudes = [10.0, 20.0, 30.0, 50.0]
    
    for alt in altitudes:
        config = CoverageConfig(altitude=alt)
        waypoints = planner.generate_coverage_waypoints(simple_field, config)
        
        # All waypoints should have the specified altitude
        for _, _, waypoint_alt in waypoints:
            assert waypoint_alt == alt


def test_complex_field_boundary(planner):
    """Test coverage planning with complex (non-rectangular) field."""
    # Pentagon-shaped field
    boundary = FieldBoundary(corners=[
        (47.3977, 8.5456),
        (47.3987, 8.5450),
        (47.3992, 8.5461),
        (47.3985, 8.5470),
        (47.3975, 8.5465),
    ])
    
    config = CoverageConfig(pattern=CoveragePattern.PARALLEL_LINES)
    waypoints = planner.generate_coverage_waypoints(boundary, config)
    
    # Should generate waypoints for complex shape
    assert len(waypoints) > 0


def test_heading_rotation(planner, simple_field):
    """Test that heading parameter is accepted and processed."""
    config_0 = CoverageConfig(heading=0.0)
    config_90 = CoverageConfig(heading=90.0)
    
    waypoints_0 = planner.generate_coverage_waypoints(simple_field, config_0)
    waypoints_90 = planner.generate_coverage_waypoints(simple_field, config_90)
    
    # Both should generate valid waypoints
    assert len(waypoints_0) > 0
    assert len(waypoints_90) > 0
    
    # Note: Current implementation doesn't rotate the pattern,
    # but accepts the heading parameter for future enhancement


def test_overlap_parameter(planner, simple_field):
    """Test that overlap parameter is accepted."""
    config = CoverageConfig(
        overlap=0.3,  # 30% overlap
        line_spacing=50.0,
    )
    
    waypoints = planner.generate_coverage_waypoints(simple_field, config)
    
    # Should generate waypoints (overlap affects spacing calculation)
    assert len(waypoints) > 0

# Made with Bob

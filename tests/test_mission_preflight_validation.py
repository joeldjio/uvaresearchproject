"""
Tests for MissionEngine pre-flight validation.
"""
from __future__ import annotations

import pytest

from droneresearch.control.mission import MissionEngine, Waypoint
from droneresearch.control.mission_validation import calculate_distance
from tests.conftest import FakeConnection


def test_validate_empty_mission():
    """Test validation fails with no waypoints."""
    conn = FakeConnection()
    mission = MissionEngine(conn)
    
    is_valid, errors = mission.validate()
    
    assert is_valid is False
    assert len(errors) == 1
    assert "no waypoints" in errors[0].lower()


def test_validate_no_connection():
    """Test validation fails without connection."""
    mission = MissionEngine(None)
    mission.add(Waypoint(lat=48.0, lon=11.0, alt=10))
    
    is_valid, errors = mission.validate()
    
    assert is_valid is False
    assert any("connection" in e.lower() for e in errors)


def test_validate_valid_mission():
    """Test validation passes with valid waypoints."""
    conn = FakeConnection()
    mission = MissionEngine(conn)
    
    mission.add(Waypoint(lat=48.0, lon=11.0, alt=10))
    mission.add(Waypoint(lat=48.001, lon=11.001, alt=20))
    mission.add(Waypoint(lat=48.002, lon=11.002, alt=15))
    
    is_valid, errors = mission.validate()
    
    assert is_valid is True
    assert len(errors) == 0


def test_validate_invalid_latitude():
    """Test validation catches invalid latitude."""
    conn = FakeConnection()
    mission = MissionEngine(conn)
    
    # Too high
    mission.add(Waypoint(lat=91.0, lon=11.0, alt=10))
    is_valid, errors = mission.validate()
    assert is_valid is False
    assert any("latitude" in e.lower() and "91" in e for e in errors)
    
    # Too low
    mission.clear()
    mission.add(Waypoint(lat=-91.0, lon=11.0, alt=10))
    is_valid, errors = mission.validate()
    assert is_valid is False
    assert any("latitude" in e.lower() and "-91" in e for e in errors)


def test_validate_invalid_longitude():
    """Test validation catches invalid longitude."""
    conn = FakeConnection()
    mission = MissionEngine(conn)
    
    # Too high
    mission.add(Waypoint(lat=48.0, lon=181.0, alt=10))
    is_valid, errors = mission.validate()
    assert is_valid is False
    assert any("longitude" in e.lower() and "181" in e for e in errors)
    
    # Too low
    mission.clear()
    mission.add(Waypoint(lat=48.0, lon=-181.0, alt=10))
    is_valid, errors = mission.validate()
    assert is_valid is False
    assert any("longitude" in e.lower() and "-181" in e for e in errors)


def test_validate_negative_altitude():
    """Test validation catches negative altitude."""
    conn = FakeConnection()
    mission = MissionEngine(conn)
    
    mission.add(Waypoint(lat=48.0, lon=11.0, alt=-5))
    
    is_valid, errors = mission.validate()
    
    assert is_valid is False
    assert any("negative altitude" in e.lower() for e in errors)


def test_validate_excessive_altitude():
    """Test validation catches excessive altitude."""
    conn = FakeConnection()
    mission = MissionEngine(conn)
    
    mission.add(Waypoint(lat=48.0, lon=11.0, alt=600))
    
    is_valid, errors = mission.validate()
    
    assert is_valid is False
    assert any("500m" in e for e in errors)


def test_validate_waypoints_too_close():
    """Test validation warns about waypoints too close together."""
    conn = FakeConnection()
    mission = MissionEngine(conn)
    
    # Two waypoints 0.5m apart (< 1m threshold)
    mission.add(Waypoint(lat=48.0, lon=11.0, alt=10))
    mission.add(Waypoint(lat=48.0000045, lon=11.0, alt=10))  # ~0.5m north
    
    is_valid, errors = mission.validate()
    
    assert is_valid is False
    assert any("too close" in e.lower() for e in errors)


def test_validate_multiple_errors():
    """Test validation reports multiple errors."""
    conn = FakeConnection()
    mission = MissionEngine(conn)
    
    mission.add(Waypoint(lat=91.0, lon=181.0, alt=-10))  # 3 errors
    mission.add(Waypoint(lat=48.0, lon=11.0, alt=600))   # 1 error
    
    is_valid, errors = mission.validate()
    
    assert is_valid is False
    assert len(errors) >= 4  # At least 4 errors


def test_validate_edge_case_coordinates():
    """Test validation with edge case but valid coordinates."""
    conn = FakeConnection()
    mission = MissionEngine(conn)
    
    # Exactly at limits (should be valid)
    mission.add(Waypoint(lat=90.0, lon=180.0, alt=0))
    mission.add(Waypoint(lat=-90.0, lon=-180.0, alt=500))
    
    is_valid, errors = mission.validate()
    
    # Should pass (at limits but not exceeding)
    assert is_valid is True
    assert len(errors) == 0


def test_upload_with_validation():
    """Test upload() runs validation by default."""
    conn = FakeConnection()
    mission = MissionEngine(conn)
    
    # Invalid mission
    mission.add(Waypoint(lat=91.0, lon=11.0, alt=10))
    
    # Should fail due to validation
    result = mission.upload()
    assert result is False


def test_upload_skip_validation():
    """Test upload() can skip validation."""
    conn = FakeConnection()
    mission = MissionEngine(conn)
    
    # Invalid mission
    mission.add(Waypoint(lat=91.0, lon=11.0, alt=10))
    
    # Should attempt upload (will fail for other reasons, but validation is skipped)
    result = mission.upload(validate_first=False)
    # Result depends on connection state, but validation was skipped


def test_calculate_distance():
    """Test distance calculation between waypoints."""
    # Munich to ~1km north
    dist = calculate_distance(48.0, 11.0, 48.009, 11.0)
    
    # Should be approximately 1000m (1km)
    assert 900 < dist < 1100


def test_calculate_distance_zero():
    """Test distance calculation for same point."""
    dist = calculate_distance(48.0, 11.0, 48.0, 11.0)
    
    assert dist == 0.0


def test_validate_single_waypoint():
    """Test validation passes with single waypoint."""
    conn = FakeConnection()
    mission = MissionEngine(conn)
    
    mission.add(Waypoint(lat=48.0, lon=11.0, alt=10))
    
    is_valid, errors = mission.validate()
    
    assert is_valid is True
    assert len(errors) == 0


def test_validate_long_mission():
    """Test validation with many waypoints."""
    conn = FakeConnection()
    mission = MissionEngine(conn)
    
    # Add 100 valid waypoints
    for i in range(100):
        mission.add(Waypoint(lat=48.0 + i * 0.001, lon=11.0 + i * 0.001, alt=10 + i))
    
    is_valid, errors = mission.validate()
    
    assert is_valid is True
    assert len(errors) == 0


def test_validate_error_messages_include_waypoint_index():
    """Test error messages include waypoint index."""
    conn = FakeConnection()
    mission = MissionEngine(conn)
    
    mission.add(Waypoint(lat=48.0, lon=11.0, alt=10))  # Valid
    mission.add(Waypoint(lat=91.0, lon=11.0, alt=10))  # Invalid
    mission.add(Waypoint(lat=48.0, lon=11.0, alt=10))  # Valid
    
    is_valid, errors = mission.validate()
    
    assert is_valid is False
    # Error should mention WP1 (second waypoint, 0-indexed)
    assert any("WP1" in e for e in errors)


# Made with Bob
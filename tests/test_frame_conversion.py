"""
Tests for NED ↔ ENU frame conversion.
"""
import pytest
from droneresearch.ros.px4_bridge import ned_to_enu, enu_to_ned, frd_to_flu


def test_ned_to_enu_basic():
    """Test basic NED to ENU conversion."""
    # NED: North=1, East=2, Down=3
    # ENU: East=2, North=1, Up=-3
    e, n, u = ned_to_enu(1.0, 2.0, 3.0)
    assert e == pytest.approx(2.0)
    assert n == pytest.approx(1.0)
    assert u == pytest.approx(-3.0)


def test_enu_to_ned_basic():
    """Test basic ENU to NED conversion."""
    # ENU: East=2, North=1, Up=3
    # NED: North=1, East=2, Down=-3
    n, e, d = enu_to_ned(2.0, 1.0, 3.0)
    assert n == pytest.approx(1.0)
    assert e == pytest.approx(2.0)
    assert d == pytest.approx(-3.0)


def test_ned_enu_roundtrip():
    """Test that NED → ENU → NED gives original values."""
    ned_n, ned_e, ned_d = 10.0, 20.0, -5.0
    
    # Convert to ENU
    enu_e, enu_n, enu_u = ned_to_enu(ned_n, ned_e, ned_d)
    
    # Convert back to NED
    back_n, back_e, back_d = enu_to_ned(enu_e, enu_n, enu_u)
    
    assert back_n == pytest.approx(ned_n)
    assert back_e == pytest.approx(ned_e)
    assert back_d == pytest.approx(ned_d)


def test_enu_ned_roundtrip():
    """Test that ENU → NED → ENU gives original values."""
    enu_e, enu_n, enu_u = 15.0, 25.0, 10.0
    
    # Convert to NED
    ned_n, ned_e, ned_d = enu_to_ned(enu_e, enu_n, enu_u)
    
    # Convert back to ENU
    back_e, back_n, back_u = ned_to_enu(ned_n, ned_e, ned_d)
    
    assert back_e == pytest.approx(enu_e)
    assert back_n == pytest.approx(enu_n)
    assert back_u == pytest.approx(enu_u)


def test_ned_to_enu_zero():
    """Test conversion at origin."""
    e, n, u = ned_to_enu(0.0, 0.0, 0.0)
    assert e == pytest.approx(0.0)
    assert n == pytest.approx(0.0)
    assert u == pytest.approx(0.0)


def test_ned_to_enu_negative():
    """Test conversion with negative values."""
    # NED: North=-5, East=-10, Down=-2 (above ground)
    # ENU: East=-10, North=-5, Up=2
    e, n, u = ned_to_enu(-5.0, -10.0, -2.0)
    assert e == pytest.approx(-10.0)
    assert n == pytest.approx(-5.0)
    assert u == pytest.approx(2.0)


def test_frd_to_flu_basic():
    """Test FRD to FLU body frame conversion."""
    # FRD: Forward=1, Right=2, Down=3
    # FLU: Forward=1, Left=-2, Up=-3
    f, l, u = frd_to_flu(1.0, 2.0, 3.0)
    assert f == pytest.approx(1.0)
    assert l == pytest.approx(-2.0)
    assert u == pytest.approx(-3.0)


def test_frd_to_flu_zero():
    """Test FRD to FLU at zero."""
    f, l, u = frd_to_flu(0.0, 0.0, 0.0)
    assert f == pytest.approx(0.0)
    assert l == pytest.approx(0.0)
    assert u == pytest.approx(0.0)


def test_altitude_sign_convention():
    """
    Test altitude sign convention.
    
    PX4 NED: Down is positive (altitude is negative)
    ROS2 ENU: Up is positive (altitude is positive)
    """
    # Drone at 10m altitude
    ned_down = -10.0  # Negative in NED
    _, _, enu_up = ned_to_enu(0.0, 0.0, ned_down)
    assert enu_up == pytest.approx(10.0)  # Positive in ENU
    
    # Convert back
    _, _, back_down = enu_to_ned(0.0, 0.0, enu_up)
    assert back_down == pytest.approx(ned_down)


def test_position_example():
    """Test realistic position example."""
    # Drone is 5m North, 3m East, 10m altitude
    ned_n, ned_e, ned_d = 5.0, 3.0, -10.0
    
    # Convert to ENU
    enu_e, enu_n, enu_u = ned_to_enu(ned_n, ned_e, ned_d)
    
    # Check ENU values
    assert enu_e == pytest.approx(3.0)   # East stays East
    assert enu_n == pytest.approx(5.0)   # North stays North
    assert enu_u == pytest.approx(10.0)  # Down=-10 becomes Up=10


def test_velocity_conversion():
    """Test velocity vector conversion."""
    # Velocity: 2 m/s North, 1 m/s East, -0.5 m/s Down (climbing)
    vn, ve, vd = 2.0, 1.0, -0.5
    
    # Convert to ENU
    enu_ve, enu_vn, enu_vu = ned_to_enu(vn, ve, vd)
    
    assert enu_ve == pytest.approx(1.0)   # East velocity
    assert enu_vn == pytest.approx(2.0)   # North velocity
    assert enu_vu == pytest.approx(0.5)   # Up velocity (climbing)


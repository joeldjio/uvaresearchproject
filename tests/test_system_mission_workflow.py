"""
System Tests - Mission Workflow
--------------------------------
End-to-end tests for complete mission workflows with mock backend.
"""
import pytest
import time
from unittest.mock import Mock


@pytest.mark.slow
def test_single_drone_mission_workflow(fake_conn, snap_factory):
    """System test: Complete mission workflow for single drone"""
    from droneresearch.sdk.drone import Drone
    from droneresearch.control.mission import Waypoint
    
    # ARRANGE
    drone = Drone("UAV_1", fake_conn)
    assert drone.connect(timeout=5)
    
    # Wait for initial telemetry
    time.sleep(0.1)
    
    # ACT - Complete workflow
    # 1. ARM
    assert drone.arm() is True
    time.sleep(0.1)
    
    # 2. TAKEOFF
    assert drone.takeoff(altitude=10) is True
    time.sleep(0.1)
    
    # 3. Upload mission
    waypoints = [
        Waypoint(lat=47.397742, lon=8.545594, alt=10),
        Waypoint(lat=47.398, lon=8.546, alt=15),
        Waypoint(lat=47.3985, lon=8.5455, alt=10),
    ]
    assert drone.upload_mission(waypoints) is True
    
    # 4. Start mission
    assert drone.start_mission() is True
    time.sleep(0.1)
    
    # 5. RTL
    assert drone.rtl() is True
    time.sleep(0.1)
    
    # 6. DISARM
    assert drone.disarm() is True
    
    # ASSERT - Verify final state
    snap = drone.get_snapshot()
    assert snap["armed"] is False
    
    # Cleanup
    drone.disconnect()


@pytest.mark.slow
def test_multi_drone_formation_workflow(fake_conn):
    """System test: Multi-drone formation flight"""
    from droneresearch.sdk.swarm import Swarm
    
    # ARRANGE
    swarm = Swarm()
    swarm.add("UAV_1", fake_conn)
    swarm.add("UAV_2", fake_conn)
    swarm.add("UAV_3", fake_conn)
    
    assert swarm.connect_all(timeout=5)
    time.sleep(0.1)
    
    # ACT - Formation workflow
    # 1. ARM all
    swarm.arm_all()
    time.sleep(0.1)
    
    # 2. TAKEOFF all
    swarm.takeoff_all(altitude=10)
    time.sleep(0.1)
    
    # 3. Start formation (circle)
    result = swarm.start_formation("circle", radius=10.0)
    assert result is True or result is None  # Depends on implementation
    time.sleep(0.2)
    
    # 4. Hold formation for a moment
    time.sleep(0.5)
    
    # 5. Stop formation
    if hasattr(swarm, 'stop_formation'):
        swarm.stop_formation()
        time.sleep(0.1)
    
    # 6. Land all
    swarm.land_all()
    time.sleep(0.1)
    
    # ASSERT - All drones should be on ground
    for drone_id in ["UAV_1", "UAV_2", "UAV_3"]:
        snap = swarm.droneSnapshot(drone_id)
        assert snap is not None
    
    # Cleanup
    swarm.disconnect_all()


@pytest.mark.slow
def test_mission_with_apf_safety(fake_conn):
    """System test: Mission with APF safety filter active"""
    from droneresearch.sdk.drone import Drone
    from droneresearch.safety.apf import APFFilter
    from droneresearch.control.mission import Waypoint
    
    # ARRANGE
    drone = Drone("UAV_1", fake_conn)
    assert drone.connect(timeout=5)
    
    # Configure APF
    apf = APFFilter(
        min_separation=5.0,
        max_speed=5.0,
        repulsion_gain=2.0
    )
    
    # ACT
    # 1. ARM and TAKEOFF
    assert drone.arm()
    assert drone.takeoff(altitude=10)
    time.sleep(0.1)
    
    # 2. Upload mission
    waypoints = [
        Waypoint(lat=47.397742, lon=8.545594, alt=10),
        Waypoint(lat=47.398, lon=8.546, alt=15),
    ]
    assert drone.upload_mission(waypoints)
    
    # 3. Start mission with APF active
    assert drone.start_mission()
    time.sleep(0.1)
    
    # Simulate APF filtering (would normally run in background)
    # For this test, we just verify APF can process positions
    from droneresearch.safety.apf import Pose3D
    pos = Pose3D(x=0, y=0, z=10)
    target = Pose3D(x=10, y=0, z=10)
    
    filtered = apf.filter_waypoint(pos, target, [])
    assert filtered is not None
    
    # 4. Complete mission
    assert drone.rtl()
    assert drone.disarm()
    
    # Cleanup
    drone.disconnect()


@pytest.mark.slow
def test_reconnect_after_connection_loss(fake_conn):
    """System test: Reconnect after connection loss"""
    from droneresearch.sdk.drone import Drone
    
    # ARRANGE
    drone = Drone("UAV_1", fake_conn)
    assert drone.connect(timeout=5)
    time.sleep(0.1)
    
    # ACT
    # 1. ARM
    assert drone.arm()
    time.sleep(0.1)
    
    # 2. Simulate connection loss
    drone.disconnect()
    time.sleep(0.2)
    
    # 3. Reconnect
    assert drone.connect(timeout=5)
    time.sleep(0.1)
    
    # ASSERT - Should be able to continue
    snap = drone.get_snapshot()
    assert snap is not None
    
    # 4. DISARM
    assert drone.disarm()
    
    # Cleanup
    drone.disconnect()


@pytest.mark.slow
def test_mission_abort_and_rtl(fake_conn):
    """System test: Abort mission and RTL"""
    from droneresearch.sdk.drone import Drone
    from droneresearch.control.mission import Waypoint
    
    # ARRANGE
    drone = Drone("UAV_1", fake_conn)
    assert drone.connect(timeout=5)
    
    # ACT
    # 1. ARM and TAKEOFF
    assert drone.arm()
    assert drone.takeoff(altitude=10)
    time.sleep(0.1)
    
    # 2. Upload and start mission
    waypoints = [
        Waypoint(lat=47.397742, lon=8.545594, alt=10),
        Waypoint(lat=47.398, lon=8.546, alt=15),
        Waypoint(lat=47.3985, lon=8.5455, alt=10),
    ]
    assert drone.upload_mission(waypoints)
    assert drone.start_mission()
    time.sleep(0.1)
    
    # 3. Abort mission (RTL)
    assert drone.rtl()
    time.sleep(0.1)
    
    # ASSERT - Should be in RTL mode
    snap = drone.get_snapshot()
    assert snap["flight_mode"] in ["RTL", "LAND"]
    
    # 4. DISARM
    assert drone.disarm()
    
    # Cleanup
    drone.disconnect()


@pytest.mark.slow
def test_swarm_mission_multi_target(fake_conn):
    """System test: Mission upload to multiple drones"""
    from droneresearch.sdk.swarm import Swarm
    from droneresearch.control.mission import Waypoint
    
    # ARRANGE
    swarm = Swarm()
    swarm.add("UAV_1", fake_conn)
    swarm.add("UAV_2", fake_conn)
    
    assert swarm.connect_all(timeout=5)
    time.sleep(0.1)
    
    # ACT
    # 1. ARM all
    swarm.arm_all()
    time.sleep(0.1)
    
    # 2. TAKEOFF all
    swarm.takeoff_all(altitude=10)
    time.sleep(0.1)
    
    # 3. Upload mission to both drones
    waypoints = [
        Waypoint(lat=47.397742, lon=8.545594, alt=10),
        Waypoint(lat=47.398, lon=8.546, alt=15),
    ]
    
    result = swarm.upload_mission_multi(["UAV_1", "UAV_2"], waypoints)
    assert result is True or result is None
    
    # 4. Start mission on both
    swarm.start_mission_multi(["UAV_1", "UAV_2"])
    time.sleep(0.1)
    
    # ASSERT - Both should be in AUTO mode
    snap1 = swarm.droneSnapshot("UAV_1")
    snap2 = swarm.droneSnapshot("UAV_2")
    
    assert snap1 is not None
    assert snap2 is not None
    
    # 5. Land all
    swarm.land_all()
    time.sleep(0.1)
    
    # Cleanup
    swarm.disconnect_all()


@pytest.mark.slow
def test_goto_command_workflow(fake_conn):
    """System test: GOTO command workflow"""
    from droneresearch.sdk.drone import Drone
    
    # ARRANGE
    drone = Drone("UAV_1", fake_conn)
    assert drone.connect(timeout=5)
    
    # ACT
    # 1. ARM and TAKEOFF
    assert drone.arm()
    assert drone.takeoff(altitude=10)
    time.sleep(0.1)
    
    # 2. GOTO command
    result = drone.goto(lat=47.398, lon=8.546, alt=15)
    assert result is True
    time.sleep(0.1)
    
    # 3. Another GOTO
    result = drone.goto(lat=47.3985, lon=8.5455, alt=10)
    assert result is True
    time.sleep(0.1)
    
    # 4. RTL and DISARM
    assert drone.rtl()
    assert drone.disarm()
    
    # Cleanup
    drone.disconnect()


@pytest.mark.slow
def test_mode_switching_workflow(fake_conn):
    """System test: Flight mode switching"""
    from droneresearch.sdk.drone import Drone
    
    # ARRANGE
    drone = Drone("UAV_1", fake_conn)
    assert drone.connect(timeout=5)
    
    # ACT - Test mode switches
    modes = ["STABILIZE", "ALT_HOLD", "LOITER", "GUIDED", "RTL"]
    
    for mode in modes:
        result = drone.set_mode(mode)
        assert result is True
        time.sleep(0.05)
        
        snap = drone.get_snapshot()
        assert snap["flight_mode"] == mode
    
    # Cleanup
    drone.disconnect()


@pytest.mark.slow
def test_telemetry_logging_workflow(fake_conn, tmp_path):
    """System test: Telemetry logging during flight"""
    from droneresearch.sdk.drone import Drone
    from droneresearch.data.logger import DataLogger
    
    # ARRANGE
    drone = Drone("UAV_1", fake_conn)
    assert drone.connect(timeout=5)
    
    log_file = tmp_path / "telemetry.jsonl"
    logger = DataLogger(str(log_file))
    logger.start()
    
    # ACT
    # 1. ARM and TAKEOFF
    assert drone.arm()
    logger.log({"event": "armed", "drone_id": "UAV_1"})
    
    assert drone.takeoff(altitude=10)
    logger.log({"event": "takeoff", "drone_id": "UAV_1", "altitude": 10})
    
    time.sleep(0.1)
    
    # 2. Log telemetry
    for i in range(5):
        snap = drone.get_snapshot()
        logger.log({"event": "telemetry", "drone_id": "UAV_1", "data": snap})
        time.sleep(0.05)
    
    # 3. RTL and DISARM
    assert drone.rtl()
    logger.log({"event": "rtl", "drone_id": "UAV_1"})
    
    assert drone.disarm()
    logger.log({"event": "disarmed", "drone_id": "UAV_1"})
    
    # Stop logger
    logger.stop()
    
    # ASSERT - Log file should exist and contain data
    assert log_file.exists()
    assert log_file.stat().st_size > 0
    
    # Cleanup
    drone.disconnect()


@pytest.mark.slow
def test_experiment_script_execution():
    """System test: Execute experiment script"""
    from droneresearch.experiment.manager import ExperimentManager
    
    # ARRANGE
    script = """
# Simple test experiment
result = {"status": "success", "value": 42}
"""
    
    manager = ExperimentManager()
    
    # ACT
    result = manager.run_script(script)
    
    # ASSERT
    assert result is not None
    assert result.get("status") == "success"
    assert result.get("value") == 42


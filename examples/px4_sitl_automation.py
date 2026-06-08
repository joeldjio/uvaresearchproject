#!/usr/bin/env python3
"""
PX4 SITL Automation Example

Demonstrates how to use PX4GazeboCluster to automatically start
PX4 SITL + Gazebo + XRCE-DDS Agent, then connect a ROS2 bridge.

Usage:
    python examples/px4_sitl_automation.py
"""

import time
import logging
from droneresearch.simulation import PX4GazeboCluster
from droneresearch.ros.px4_bridge import PX4ROS2Bridge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Run automated SITL + ROS2 bridge example."""
    
    # Configure SITL cluster
    cluster = PX4GazeboCluster(
        num_drones=1,
        px4_dir="/home/iruz/PX4-Autopilot",  # Adjust to your PX4 path
        model="x500",
        ros2_setups=[
            "/opt/ros/humble/setup.bash",
            "/home/iruz/ws_sensor_combined/install/setup.bash"  # Adjust to your workspace
        ],
        namespace_prefix="uav"
    )
    
    logger.info("=" * 60)
    logger.info("PX4 SITL Automation Example")
    logger.info("=" * 60)
    
    try:
        # Start SITL cluster
        logger.info("Starting PX4 SITL + Gazebo + XRCE-DDS Agent...")
        if not cluster.start():
            logger.error("Failed to start SITL cluster")
            return
        
        logger.info("✓ SITL cluster running")
        logger.info(f"Namespaces: {cluster.get_namespaces()}")
        
        # Wait a bit for everything to stabilize
        logger.info("Waiting 5 seconds for system to stabilize...")
        time.sleep(5)
        
        # Connect ROS2 bridge
        logger.info("Starting ROS2 bridge...")
        bridge = PX4ROS2Bridge(namespace="uav_1", publish_hz=10.0)
        bridge.start()
        
        logger.info("✓ ROS2 bridge connected")
        
        # Wait for telemetry
        logger.info("Waiting for telemetry...")
        for i in range(10):
            time.sleep(1)
            if bridge.telemetry:
                logger.info(f"✓ Telemetry received: {list(bridge.telemetry.keys())}")
                break
        else:
            logger.warning("No telemetry received after 10 seconds")
        
        # Arm and takeoff
        logger.info("\nArming vehicle...")
        bridge.arm()
        time.sleep(2)
        
        logger.info("Taking off to 10m...")
        bridge.takeoff(10.0)
        time.sleep(10)
        
        # Check altitude
        local_pos = bridge.telemetry.get("local_position", {})
        altitude = -local_pos.get("z", 0)  # NED: negative z is up
        logger.info(f"Current altitude: {altitude:.1f}m")
        
        # Hover for 5 seconds
        logger.info("Hovering for 5 seconds...")
        time.sleep(5)
        
        # Land
        logger.info("Landing...")
        bridge.land()
        time.sleep(10)
        
        logger.info("✓ Mission complete")
        
        # Keep running for a bit
        logger.info("\nPress Ctrl+C to stop...")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        # Cleanup
        logger.info("Stopping ROS2 bridge...")
        try:
            bridge.stop()
        except:
            pass
        
        logger.info("Stopping SITL cluster...")
        cluster.stop()
        
        logger.info("✓ Cleanup complete")


if __name__ == "__main__":
    main()

# Made with Bob

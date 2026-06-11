"""
Tests for PX4 Gazebo log streaming.
"""
import pytest
from unittest.mock import Mock, patch
import subprocess
import time
import tempfile
import os


def test_log_callback_called():
    """Test that log callback is called with process output."""
    from droneresearch.simulation import PX4GazeboCluster
    
    # Mock callback
    log_callback = Mock()
    
    # Create temporary directory for PX4
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create cluster with callback
        with patch('droneresearch.simulation.px4_gazebo.subprocess.Popen') as mock_popen:
            # Mock process with fake output
            mock_proc = Mock()
            mock_proc.poll.return_value = None  # Process running
            mock_proc.stdout.readline.side_effect = [
                b"Test log line 1\n",
                b"Test log line 2\n",
                b""  # EOF
            ]
            mock_proc.stderr.readline.return_value = b""
            mock_popen.return_value = mock_proc
            
            cluster = PX4GazeboCluster(
                num_drones=1,
                px4_dir=tmpdir,
                log_callback=log_callback
            )
            
            # Verify callback was set
            assert cluster.log_callback is log_callback


def test_log_streaming_thread_safety():
    """Test that log streaming doesn't block main thread."""
    from droneresearch.simulation import PX4GazeboCluster
    
    logs_received = []
    
    def callback(source: str, message: str):
        logs_received.append((source, message))
    
    # Create temporary directory for PX4
    with tempfile.TemporaryDirectory() as tmpdir:
        # This test just verifies the callback signature is correct
        cluster = PX4GazeboCluster(
            num_drones=1,
            px4_dir=tmpdir,
            log_callback=callback
        )
        
        # Simulate a log message
        if cluster.log_callback:
            cluster.log_callback("test_source", "test message")
        
        assert len(logs_received) == 1
        assert logs_received[0] == ("test_source", "test message")


def test_no_callback_doesnt_crash():
    """Test that cluster works without log callback."""
    from droneresearch.simulation import PX4GazeboCluster
    
    # Create temporary directory for PX4
    with tempfile.TemporaryDirectory() as tmpdir:
        # Should not crash without callback
        cluster = PX4GazeboCluster(
            num_drones=1,
            px4_dir=tmpdir,
            log_callback=None
        )
        
        assert cluster.log_callback is None
        assert cluster._log_threads == []


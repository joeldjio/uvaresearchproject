"""
ROS2 Bag Playback Context for UI

Provides video-player-like controls for ROS2 bag file playback.
Manages subprocess for `ros2 bag play` command.
"""
from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, pyqtProperty


class BagPlaybackContext(QObject):
    """
    Context for controlling ROS2 bag playback.
    
    Signals:
        stateChanged: Playback state changed (stopped/playing/paused)
        progressChanged: Playback progress changed (0.0-1.0)
        durationChanged: Total duration discovered (seconds)
        errorOccurred: Error during playback
    """
    
    stateChanged = pyqtSignal(str)  # "stopped", "playing", "paused"
    progressChanged = pyqtSignal(float)  # 0.0 to 1.0
    durationChanged = pyqtSignal(float)  # seconds
    playbackRateChanged = pyqtSignal(float)  # playback speed
    errorOccurred = pyqtSignal(str)
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._state = "stopped"
        self._progress = 0.0
        self._duration = 0.0
        self._playback_rate = 1.0
        self._bag_path: Optional[Path] = None
        self._process: Optional[subprocess.Popen] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitoring = False
    
    @pyqtProperty(str, notify=stateChanged)
    def state(self) -> str:
        """Current playback state: stopped/playing/paused"""
        return self._state
    
    @pyqtProperty(float, notify=progressChanged)
    def progress(self) -> float:
        """Playback progress (0.0 to 1.0)"""
        return self._progress
    
    @pyqtProperty(float, notify=durationChanged)
    def duration(self) -> float:
        """Total duration in seconds"""
        return self._duration
    
    @pyqtProperty(float, notify=playbackRateChanged)
    def playbackRate(self) -> float:
        """Playback speed multiplier"""
        return self._playback_rate
    
    @playbackRate.setter
    def playbackRate(self, rate: float):
        """Set playback speed (0.1 to 10.0)"""
        new_rate = max(0.1, min(10.0, rate))
        if new_rate != self._playback_rate:
            self._playback_rate = new_rate
            self.playbackRateChanged.emit(self._playback_rate)
    
    @pyqtSlot(str)
    def loadBag(self, path: str) -> None:
        """
        Load a ROS2 bag file.
        
        Args:
            path: Path to .mcap or bag directory
        """
        try:
            bag_path = Path(path)
            if not bag_path.exists():
                self.errorOccurred.emit(f"Bag file not found: {path}")
                return
            
            # Stop any existing playback
            if self._state != "stopped":
                self.stop()
            
            self._bag_path = bag_path
            
            # Get bag info to determine duration
            self._get_bag_info()
            
        except Exception as e:
            self.errorOccurred.emit(f"Failed to load bag: {e}")
    
    def _get_bag_info(self) -> None:
        """Extract bag metadata (duration, topics, etc.)"""
        if not self._bag_path:
            return
        
        try:
            # Run `ros2 bag info` to get metadata
            result = subprocess.run(
                ["ros2", "bag", "info", str(self._bag_path)],
                capture_output=True,
                text=True,
                timeout=5.0
            )
            
            if result.returncode != 0:
                self.errorOccurred.emit(f"Failed to get bag info: {result.stderr}")
                return
            
            # Parse duration from output (format: "Duration: 123.45s")
            for line in result.stdout.split('\n'):
                if 'Duration:' in line:
                    duration_str = line.split('Duration:')[1].strip().rstrip('s')
                    self._duration = float(duration_str)
                    self.durationChanged.emit(self._duration)
                    break
        
        except subprocess.TimeoutExpired:
            self.errorOccurred.emit("Timeout getting bag info")
        except Exception as e:
            self.errorOccurred.emit(f"Error parsing bag info: {e}")
    
    @pyqtSlot()
    def play(self) -> None:
        """Start or resume playback"""
        if not self._bag_path:
            self.errorOccurred.emit("No bag file loaded")
            return
        
        if self._state == "playing":
            return  # Already playing
        
        try:
            # Build ros2 bag play command
            cmd = [
                "ros2", "bag", "play",
                str(self._bag_path),
                "--rate", str(self._playback_rate),
                "--clock"  # Publish /clock for simulation time
            ]
            
            # Start subprocess
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Update state
            self._state = "playing"
            self.stateChanged.emit(self._state)
            
            # Start monitoring thread
            self._stop_monitoring = False
            self._monitor_thread = threading.Thread(target=self._monitor_playback, daemon=True)
            self._monitor_thread.start()
        
        except Exception as e:
            self.errorOccurred.emit(f"Failed to start playback: {e}")
    
    @pyqtSlot()
    def pause(self) -> None:
        """Pause playback (not supported by ros2 bag play - will stop instead)"""
        # Note: ros2 bag play doesn't support pause, so we stop
        self.stop()
    
    @pyqtSlot()
    def stop(self) -> None:
        """Stop playback"""
        if self._process:
            self._stop_monitoring = True
            self._process.terminate()
            try:
                self._process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
            self._monitor_thread = None
        
        self._state = "stopped"
        self._progress = 0.0
        self.stateChanged.emit(self._state)
        self.progressChanged.emit(self._progress)
    
    @pyqtSlot(float)
    def seek(self, position: float) -> None:
        """
        Seek to position (0.0 to 1.0).
        
        Note: ros2 bag play doesn't support seeking, so this will
        restart playback from the beginning with --start-offset.
        """
        if not self._bag_path or self._duration <= 0:
            return
        
        # Calculate time offset
        offset = position * self._duration
        
        # Stop current playback
        was_playing = self._state == "playing"
        self.stop()
        
        # Restart with offset
        try:
            cmd = [
                "ros2", "bag", "play",
                str(self._bag_path),
                "--rate", str(self._playback_rate),
                "--clock",
                "--start-offset", str(offset)
            ]
            
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self._state = "playing"
            self._progress = position
            self.stateChanged.emit(self._state)
            self.progressChanged.emit(self._progress)
            
            # Restart monitoring
            self._stop_monitoring = False
            self._monitor_thread = threading.Thread(target=self._monitor_playback, daemon=True)
            self._monitor_thread.start()
        
        except Exception as e:
            self.errorOccurred.emit(f"Failed to seek: {e}")
    
    def _monitor_playback(self) -> None:
        """Monitor playback progress (runs in background thread)"""
        start_time = time.time()
        
        while not self._stop_monitoring and self._process:
            # Check if process is still running
            if self._process.poll() is not None:
                # Process ended
                self._state = "stopped"
                self._progress = 1.0
                self.stateChanged.emit(self._state)
                self.progressChanged.emit(self._progress)
                break
            
            # Update progress based on elapsed time
            if self._duration > 0:
                elapsed = (time.time() - start_time) * self._playback_rate
                self._progress = min(1.0, elapsed / self._duration)
                self.progressChanged.emit(self._progress)
            
            time.sleep(0.1)  # Update at 10Hz
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        self.stop()

# Made with Bob

"""
Smart Battery Monitor — Intelligent battery monitoring with predictive RTL.

Monitors battery levels and triggers automatic Return-to-Launch (RTL) when:
1. Battery drops below critical threshold, OR
2. Estimated remaining flight time < RTL time + safety margin

Features:
- Predictive RTL based on power consumption history
- Distance-to-home calculation
- Power consumption tracking (mAh/km)
- Configurable thresholds and safety margins
- Per-drone monitoring with independent triggers

Usage:
    from droneresearch.safety.battery_monitor import BatteryMonitor
    
    monitor = BatteryMonitor(
        critical_threshold=20,    # % battery
        warning_threshold=30,     # % battery
        safety_margin=1.2         # 20% safety margin for RTL
    )
    
    # Start monitoring a drone
    monitor.start_monitoring(drone)
    
    # Check if RTL should be triggered
    should_rtl, reason = monitor.should_trigger_rtl(drone)
    if should_rtl:
        print(f"RTL triggered: {reason}")
        drone.rtl()
    
    # Get battery predictions
    rtl_time, battery_required = monitor.calculate_rtl_requirements(drone)
    print(f"RTL needs {rtl_time:.1f}s and {battery_required:.1f}% battery")
"""

import math
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Callable


@dataclass
class PowerSample:
    """Power consumption sample."""
    timestamp: float
    battery_pct: float
    position: Tuple[float, float, float]  # (lat, lon, alt)
    distance_traveled: float  # meters since last sample


@dataclass
class BatteryStatus:
    """Current battery status for a drone."""
    battery_pct: float
    voltage: float
    current: float
    estimated_time_remaining: float  # seconds
    rtl_time_required: float  # seconds
    rtl_battery_required: float  # percent
    should_rtl: bool
    rtl_reason: str


class BatteryMonitor:
    """
    Intelligent battery monitoring with predictive RTL.
    
    Tracks power consumption over time and predicts when RTL should
    be triggered to ensure safe return home.
    """
    
    def __init__(
        self,
        critical_threshold: float = 20.0,
        warning_threshold: float = 30.0,
        safety_margin: float = 1.2,
        history_size: int = 100,
        min_samples_for_prediction: int = 10
    ):
        """
        Initialize battery monitor.
        
        Args:
            critical_threshold: Battery % below which RTL is always triggered
            warning_threshold: Battery % for warnings
            safety_margin: Multiplier for RTL time (1.2 = 20% safety margin)
            history_size: Number of power samples to keep
            min_samples_for_prediction: Minimum samples needed for prediction
        """
        self.critical_threshold = critical_threshold
        self.warning_threshold = warning_threshold
        self.safety_margin = safety_margin
        self.min_samples = min_samples_for_prediction
        
        # Per-drone monitoring data
        self._monitoring: Dict[str, bool] = {}
        self._power_history: Dict[str, deque] = {}
        self._last_sample: Dict[str, PowerSample] = {}
        self._rtl_triggered: Dict[str, bool] = {}
        self._callbacks: Dict[str, Callable] = {}
        
        self._lock = threading.Lock()
    
    def start_monitoring(self, drone_id: str, callback: Optional[Callable] = None):
        """
        Start monitoring a drone's battery.
        
        Args:
            drone_id: Unique drone identifier
            callback: Optional callback(drone_id, status) called on status updates
        """
        with self._lock:
            self._monitoring[drone_id] = True
            self._power_history[drone_id] = deque(maxlen=100)
            self._rtl_triggered[drone_id] = False
            if callback:
                self._callbacks[drone_id] = callback
    
    def stop_monitoring(self, drone_id: str):
        """Stop monitoring a drone."""
        with self._lock:
            self._monitoring.pop(drone_id, None)
            self._power_history.pop(drone_id, None)
            self._last_sample.pop(drone_id, None)
            self._rtl_triggered.pop(drone_id, None)
            self._callbacks.pop(drone_id, None)
    
    def update(self, drone_id: str, telemetry: dict):
        """
        Update battery status with new telemetry.
        
        Args:
            drone_id: Drone identifier
            telemetry: Telemetry dict with keys:
                - battery_pct: Battery percentage
                - battery_v: Voltage
                - current_a: Current draw (optional)
                - lat, lon, alt_rel: Position
        """
        if not self._monitoring.get(drone_id):
            return
        
        battery_pct = telemetry.get("battery_pct", 0)
        lat = telemetry.get("lat", 0)
        lon = telemetry.get("lon", 0)
        alt = telemetry.get("alt_rel", 0)
        
        if battery_pct <= 0 or lat == 0 or lon == 0:
            return
        
        with self._lock:
            # Calculate distance traveled since last sample
            distance = 0.0
            last = self._last_sample.get(drone_id)
            if last:
                distance = self._calculate_distance(
                    (last.position[0], last.position[1]),
                    (lat, lon)
                )
            
            # Create new sample
            sample = PowerSample(
                timestamp=time.time(),
                battery_pct=battery_pct,
                position=(lat, lon, alt),
                distance_traveled=distance
            )
            
            self._power_history[drone_id].append(sample)
            self._last_sample[drone_id] = sample
    
    def should_trigger_rtl(self, drone_id: str, home_position: Tuple[float, float, float]) -> Tuple[bool, str]:
        """
        Check if RTL should be triggered for a drone.
        
        Args:
            drone_id: Drone identifier
            home_position: Home position (lat, lon, alt)
        
        Returns:
            (should_trigger, reason) tuple
        """
        if not self._monitoring.get(drone_id):
            return False, ""
        
        if self._rtl_triggered.get(drone_id):
            return False, "RTL already triggered"
        
        with self._lock:
            history = self._power_history.get(drone_id, deque())
            if not history:
                return False, ""
            
            current_sample = history[-1]
            battery_pct = current_sample.battery_pct
            
            # Check critical threshold
            if battery_pct < self.critical_threshold:
                self._rtl_triggered[drone_id] = True
                return True, f"Critical battery: {battery_pct:.1f}%"
            
            # Check predictive RTL
            if len(history) >= self.min_samples:
                rtl_time, battery_required = self._calculate_rtl_requirements(
                    drone_id,
                    current_sample.position,
                    home_position,
                    history
                )
                
                if rtl_time > 0 and battery_required > 0:
                    # Trigger if current battery < required battery
                    if battery_pct < battery_required:
                        self._rtl_triggered[drone_id] = True
                        return True, f"Insufficient battery for RTL: {battery_pct:.1f}% < {battery_required:.1f}%"
            
            return False, ""
    
    def get_battery_status(self, drone_id: str, home_position: Tuple[float, float, float]) -> Optional[BatteryStatus]:
        """
        Get comprehensive battery status for a drone.
        
        Args:
            drone_id: Drone identifier
            home_position: Home position (lat, lon, alt)
        
        Returns:
            BatteryStatus object or None if not monitoring
        """
        if not self._monitoring.get(drone_id):
            return None
        
        with self._lock:
            history = self._power_history.get(drone_id, deque())
            if not history:
                return None
            
            current_sample = history[-1]
            battery_pct = current_sample.battery_pct
            
            # Calculate RTL requirements
            rtl_time = 0.0
            battery_required = 0.0
            if len(history) >= self.min_samples:
                rtl_time, battery_required = self._calculate_rtl_requirements(
                    drone_id,
                    current_sample.position,
                    home_position,
                    history
                )
            
            # Estimate remaining time
            power_rate = self._calculate_power_consumption_rate(history)
            time_remaining = 0.0
            if power_rate > 0:
                time_remaining = (battery_pct / power_rate) * 60  # seconds
            
            # Check if RTL should be triggered (internal check, no lock needed)
            should_rtl = False
            reason = ""
            
            if self._rtl_triggered.get(drone_id):
                should_rtl = True
                reason = "RTL already triggered"
            elif battery_pct < self.critical_threshold:
                should_rtl = True
                reason = f"Critical battery: {battery_pct:.1f}%"
            elif len(history) >= self.min_samples and rtl_time > 0 and battery_required > 0:
                if battery_pct < battery_required:
                    should_rtl = True
                    reason = f"Insufficient battery for RTL: {battery_pct:.1f}% < {battery_required:.1f}%"
            
            return BatteryStatus(
                battery_pct=battery_pct,
                voltage=0.0,  # TODO: Add voltage tracking
                current=0.0,  # TODO: Add current tracking
                estimated_time_remaining=time_remaining,
                rtl_time_required=rtl_time,
                rtl_battery_required=battery_required,
                should_rtl=should_rtl,
                rtl_reason=reason
            )
    
    def _calculate_rtl_requirements(
        self,
        drone_id: str,
        current_pos: Tuple[float, float, float],
        home_pos: Tuple[float, float, float],
        history: deque
    ) -> Tuple[float, float]:
        """
        Calculate time and battery required for RTL.
        
        Returns:
            (rtl_time_seconds, battery_percent_required)
        """
        # Calculate distance to home
        distance_to_home = self._calculate_distance(
            (current_pos[0], current_pos[1]),
            (home_pos[0], home_pos[1])
        )
        
        # Calculate average speed from history
        avg_speed = self._calculate_average_speed(history)
        if avg_speed <= 0:
            avg_speed = 5.0  # Default 5 m/s
        
        # Calculate RTL time
        rtl_time = distance_to_home / avg_speed
        
        # Add altitude change time (assume 2 m/s climb/descent)
        alt_diff = abs(current_pos[2] - home_pos[2])
        rtl_time += alt_diff / 2.0
        
        # Apply safety margin
        rtl_time *= self.safety_margin
        
        # Calculate battery required
        power_rate = self._calculate_power_consumption_rate(history)
        if power_rate <= 0:
            power_rate = 1.0  # Default 1% per minute
        
        battery_required = (rtl_time / 60.0) * power_rate
        
        # Add minimum reserve
        battery_required = max(battery_required, self.critical_threshold)
        
        return rtl_time, battery_required
    
    def _calculate_distance(self, pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
        """Calculate distance between two GPS coordinates (Haversine formula)."""
        lat1, lon1 = pos1
        lat2, lon2 = pos2
        
        R = 6371000  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        
        a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _calculate_average_speed(self, history: deque) -> float:
        """Calculate average speed from power history."""
        if len(history) < 2:
            return 0.0
        
        total_distance = sum(s.distance_traveled for s in history)
        total_time = history[-1].timestamp - history[0].timestamp
        
        if total_time <= 0:
            return 0.0
        
        return total_distance / total_time
    
    def _calculate_power_consumption_rate(self, history: deque) -> float:
        """
        Calculate power consumption rate (% per minute).
        
        Returns:
            Power consumption rate in % per minute
        """
        if len(history) < 2:
            return 0.0
        
        battery_drop = history[0].battery_pct - history[-1].battery_pct
        time_elapsed = (history[-1].timestamp - history[0].timestamp) / 60.0  # minutes
        
        if time_elapsed <= 0 or battery_drop <= 0:
            return 0.0
        
        return battery_drop / time_elapsed
    
    def reset_rtl_trigger(self, drone_id: str):
        """Reset RTL trigger flag (e.g., after manual override)."""
        with self._lock:
            self._rtl_triggered[drone_id] = False


__all__ = ["BatteryMonitor", "BatteryStatus", "PowerSample"]

# Made with Bob

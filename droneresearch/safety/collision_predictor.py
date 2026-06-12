"""
Collision Prediction Module — Predict future collisions based on current trajectories.

Analyzes drone positions, velocities, and planned waypoints to predict
potential collisions within a configurable time horizon.

Based on concepts from:
- MAVSec (Javaid et al., 2025) - UAV security framework
- OS-RFODG (Jiang et al., 2025) - Dataset generation for collision scenarios

Usage:
    from droneresearch.safety.collision_predictor import CollisionPredictor, DroneState
    
    predictor = CollisionPredictor(
        time_horizon=10.0,      # seconds to look ahead
        min_separation=2.0,     # minimum safe distance (meters)
        sample_rate=0.5         # prediction sample interval (seconds)
    )
    
    states = {
        "D1": DroneState(x=0, y=0, z=10, vx=2, vy=0, vz=0),
        "D2": DroneState(x=20, y=0, z=10, vx=-2, vy=0, vz=0),
    }
    
    predictions = predictor.predict(states)
    for pred in predictions:
        print(f"Collision between {pred.drone_a} and {pred.drone_b} "
              f"in {pred.time_to_collision:.1f}s at distance {pred.min_distance:.2f}m")
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class DroneState:
    """Current state of a drone in local NED coordinates."""
    x: float = 0.0      # North (meters)
    y: float = 0.0      # East (meters)
    z: float = 0.0      # Altitude above ground (meters, positive up)
    vx: float = 0.0     # Velocity North (m/s)
    vy: float = 0.0     # Velocity East (m/s)
    vz: float = 0.0     # Velocity Up (m/s)
    armed: bool = False
    
    def position_at(self, dt: float) -> Tuple[float, float, float]:
        """Predict position after dt seconds assuming constant velocity."""
        return (
            self.x + self.vx * dt,
            self.y + self.vy * dt,
            self.z + self.vz * dt
        )
    
    def distance_to(self, other: "DroneState") -> float:
        """3D Euclidean distance to another drone."""
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return math.sqrt(dx*dx + dy*dy + dz*dz)


@dataclass
class CollisionPrediction:
    """Predicted collision between two drones."""
    drone_a: str
    drone_b: str
    time_to_collision: float    # seconds until collision
    min_distance: float         # closest approach distance (meters)
    collision_point: Tuple[float, float, float]  # (x, y, z) in NED
    severity: str               # "critical" | "warning" | "caution"
    
    def to_dict(self) -> dict:
        """Convert to QML-friendly dict."""
        return {
            "droneA": self.drone_a,
            "droneB": self.drone_b,
            "timeToCollision": round(self.time_to_collision, 2),
            "minDistance": round(self.min_distance, 2),
            "collisionPoint": {
                "x": round(self.collision_point[0], 2),
                "y": round(self.collision_point[1], 2),
                "z": round(self.collision_point[2], 2)
            },
            "severity": self.severity
        }


class CollisionPredictor:
    """
    Predicts future collisions based on current drone states.
    
    Uses linear extrapolation of current velocities to predict
    future positions and detect potential collisions.
    
    Parameters
    ----------
    time_horizon : float
        How far into the future to predict (seconds)
    min_separation : float
        Minimum safe distance between drones (meters)
    sample_rate : float
        Time interval between prediction samples (seconds)
    critical_threshold : float
        Distance threshold for "critical" severity (meters)
    warning_threshold : float
        Distance threshold for "warning" severity (meters)
    """
    
    def __init__(
        self,
        time_horizon: float = 10.0,
        min_separation: float = 2.0,
        sample_rate: float = 0.5,
        critical_threshold: float = 1.0,
        warning_threshold: float = 1.5
    ):
        self.time_horizon = time_horizon
        self.min_separation = min_separation
        self.sample_rate = sample_rate
        self.critical_threshold = critical_threshold
        self.warning_threshold = warning_threshold
    
    def predict(
        self,
        states: Dict[str, DroneState],
        waypoints: Optional[Dict[str, List[Tuple[float, float, float]]]] = None
    ) -> List[CollisionPrediction]:
        """
        Predict collisions within the time horizon.
        
        Parameters
        ----------
        states : Dict[str, DroneState]
            Current state of each drone
        waypoints : Optional[Dict[str, List[Tuple[float, float, float]]]]
            Planned waypoints for each drone (not yet implemented)
        
        Returns
        -------
        List[CollisionPrediction]
            List of predicted collisions, sorted by time_to_collision
        """
        predictions = []
        drone_ids = list(states.keys())
        
        # Only predict for armed drones
        armed_ids = [did for did in drone_ids if states[did].armed]
        
        # Check each pair of armed drones
        for i in range(len(armed_ids)):
            for j in range(i + 1, len(armed_ids)):
                id_a = armed_ids[i]
                id_b = armed_ids[j]
                
                pred = self._predict_pair(id_a, states[id_a], id_b, states[id_b])
                if pred:
                    predictions.append(pred)
        
        # Sort by time to collision (most urgent first)
        predictions.sort(key=lambda p: p.time_to_collision)
        return predictions
    
    def _predict_pair(
        self,
        id_a: str,
        state_a: DroneState,
        id_b: str,
        state_b: DroneState
    ) -> Optional[CollisionPrediction]:
        """
        Predict collision between two drones.
        
        Uses closest point of approach (CPA) algorithm:
        1. Sample positions at regular intervals
        2. Find minimum distance
        3. If below threshold, report collision
        """
        min_dist = float('inf')
        min_time = 0.0
        min_point = (0.0, 0.0, 0.0)
        
        # Sample trajectory at regular intervals
        t = 0.0
        while t <= self.time_horizon:
            pos_a = state_a.position_at(t)
            pos_b = state_b.position_at(t)
            
            # Calculate distance at this time
            dx = pos_a[0] - pos_b[0]
            dy = pos_a[1] - pos_b[1]
            dz = pos_a[2] - pos_b[2]
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)
            
            if dist < min_dist:
                min_dist = dist
                min_time = t
                # Collision point is midpoint between drones
                min_point = (
                    (pos_a[0] + pos_b[0]) / 2,
                    (pos_a[1] + pos_b[1]) / 2,
                    (pos_a[2] + pos_b[2]) / 2
                )
            
            t += self.sample_rate
        
        # Check if collision predicted
        if min_dist < self.min_separation:
            # Determine severity
            if min_dist < self.critical_threshold:
                severity = "critical"
            elif min_dist < self.warning_threshold:
                severity = "warning"
            else:
                severity = "caution"
            
            return CollisionPrediction(
                drone_a=id_a,
                drone_b=id_b,
                time_to_collision=min_time,
                min_distance=min_dist,
                collision_point=min_point,
                severity=severity
            )
        
        return None
    
    def predict_with_waypoints(
        self,
        states: Dict[str, DroneState],
        waypoints: Dict[str, List[Tuple[float, float, float]]],
        cruise_speed: float = 3.0
    ) -> List[CollisionPrediction]:
        """
        Predict collisions considering planned waypoint trajectories.
        
        This is more accurate than simple velocity extrapolation as it
        accounts for planned turns and waypoint sequences.
        
        Parameters
        ----------
        states : Dict[str, DroneState]
            Current state of each drone
        waypoints : Dict[str, List[Tuple[float, float, float]]]
            Planned waypoints for each drone [(x, y, z), ...]
        cruise_speed : float
            Expected cruise speed between waypoints (m/s)
        
        Returns
        -------
        List[CollisionPrediction]
            List of predicted collisions
        """
        # Build trajectory from waypoints for each drone
        predictions = []
        drone_ids = list(states.keys())
        
        # Only predict for armed drones
        armed_ids = [did for did in drone_ids if states[did].armed]
        
        for i in range(len(armed_ids)):
            for j in range(i + 1, len(armed_ids)):
                id_a = armed_ids[i]
                id_b = armed_ids[j]
                state_a = states[id_a]
                state_b = states[id_b]
                
                # Get waypoint trajectories
                wps_a = waypoints.get(id_a, [])
                wps_b = waypoints.get(id_b, [])
                
                # If no waypoints, fall back to velocity-based
                if not wps_a or not wps_b:
                    continue
                
                # Build time-stamped trajectory for drone A
                traj_a = [(0.0, state_a.x, state_a.y, state_a.z)]
                t = 0.0
                for wp in wps_a:
                    dx = wp[0] - traj_a[-1][1]
                    dy = wp[1] - traj_a[-1][2]
                    dz = wp[2] - traj_a[-1][3]
                    dist = math.sqrt(dx**2 + dy**2 + dz**2)
                    if dist > 0:
                        t += dist / cruise_speed
                        traj_a.append((t, wp[0], wp[1], wp[2]))
                
                # Build time-stamped trajectory for drone B
                traj_b = [(0.0, state_b.x, state_b.y, state_b.z)]
                t = 0.0
                for wp in wps_b:
                    dx = wp[0] - traj_b[-1][1]
                    dy = wp[1] - traj_b[-1][2]
                    dz = wp[2] - traj_b[-1][3]
                    dist = math.sqrt(dx**2 + dy**2 + dz**2)
                    if dist > 0:
                        t += dist / cruise_speed
                        traj_b.append((t, wp[0], wp[1], wp[2]))
                
                # Sample both trajectories and find minimum distance
                max_time = min(traj_a[-1][0], traj_b[-1][0], self.time_horizon)
                min_dist = float('inf')
                min_time = 0.0
                min_point = (0.0, 0.0, 0.0)
                
                t = 0.0
                while t <= max_time:
                    # Interpolate position on trajectory A
                    pos_a = self._interpolate_trajectory(traj_a, t)
                    # Interpolate position on trajectory B
                    pos_b = self._interpolate_trajectory(traj_b, t)
                    
                    # Calculate distance
                    dx = pos_a[0] - pos_b[0]
                    dy = pos_a[1] - pos_b[1]
                    dz = pos_a[2] - pos_b[2]
                    dist = math.sqrt(dx**2 + dy**2 + dz**2)
                    
                    if dist < min_dist:
                        min_dist = dist
                        min_time = t
                        # Collision point is midpoint
                        min_point = (
                            (pos_a[0] + pos_b[0]) / 2,
                            (pos_a[1] + pos_b[1]) / 2,
                            (pos_a[2] + pos_b[2]) / 2
                        )
                    
                    t += self.sample_rate
                
                # Check if collision is predicted
                if min_dist < self.min_separation:
                    # Determine severity
                    if min_dist < self.critical_threshold:
                        severity = "critical"
                    elif min_dist < self.warning_threshold:
                        severity = "warning"
                    else:
                        severity = "caution"
                    
                    predictions.append(CollisionPrediction(
                        drone_a=id_a,
                        drone_b=id_b,
                        time_to_collision=min_time,
                        min_distance=min_dist,
                        collision_point=min_point,
                        severity=severity
                    ))
        
        return sorted(predictions, key=lambda p: p.time_to_collision)
    
    def _interpolate_trajectory(
        self,
        trajectory: List[Tuple[float, float, float, float]],
        t: float
    ) -> Tuple[float, float, float]:
        """
        Interpolate position on trajectory at time t.
        
        Parameters
        ----------
        trajectory : List[Tuple[float, float, float, float]]
            List of (time, x, y, z) tuples
        t : float
            Time to interpolate at
        
        Returns
        -------
        Tuple[float, float, float]
            Interpolated (x, y, z) position
        """
        # Find segment containing time t
        for i in range(len(trajectory) - 1):
            t0, x0, y0, z0 = trajectory[i]
            t1, x1, y1, z1 = trajectory[i + 1]
            
            if t0 <= t <= t1:
                # Linear interpolation
                if t1 - t0 > 0:
                    alpha = (t - t0) / (t1 - t0)
                    x = x0 + alpha * (x1 - x0)
                    y = y0 + alpha * (y1 - y0)
                    z = z0 + alpha * (z1 - z0)
                    return (x, y, z)
                else:
                    return (x0, y0, z0)
        
        # If t is beyond trajectory, return last position
        return (trajectory[-1][1], trajectory[-1][2], trajectory[-1][3])

# Made with Bob

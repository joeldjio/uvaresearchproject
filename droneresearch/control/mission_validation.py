"""
Mission validation utilities.

Shared validation logic for mission waypoints across different autopilot types.
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple


def validate_waypoints(waypoints: List[Dict]) -> Tuple[bool, List[str]]:
    """
    Validate mission waypoints.
    
    Checks:
    - Minimum waypoint count (at least 1)
    - Valid coordinates (lat: -90 to 90, lon: -180 to 180)
    - Reasonable altitudes (0 to 500m)
    - Waypoint spacing (warn if < 1m apart)
    
    Args:
        waypoints: List of waypoint dicts with keys: lat, lon, alt
    
    Returns:
        (is_valid, list_of_errors)
    """
    errors = []
    
    # Check waypoint count
    if len(waypoints) == 0:
        errors.append("Mission has no waypoints")
        return False, errors
    
    # Validate each waypoint
    for i, wp in enumerate(waypoints):
        # Check required fields
        if "lat" not in wp or "lon" not in wp:
            errors.append(f"WP{i}: Missing lat/lon coordinates")
            continue
        
        lat = wp["lat"]
        lon = wp["lon"]
        alt = wp.get("alt", 0)
        
        # Latitude range
        if not (-90 <= lat <= 90):
            errors.append(f"WP{i}: Invalid latitude {lat} (must be -90 to 90)")
        
        # Longitude range
        if not (-180 <= lon <= 180):
            errors.append(f"WP{i}: Invalid longitude {lon} (must be -180 to 180)")
        
        # Altitude range (reasonable limits)
        if alt < 0:
            errors.append(f"WP{i}: Negative altitude {alt}m")
        elif alt > 500:
            errors.append(f"WP{i}: Altitude {alt}m exceeds 500m limit")
        
        # Check spacing to previous waypoint
        if i > 0:
            prev = waypoints[i - 1]
            if "lat" in prev and "lon" in prev:
                dist = calculate_distance(prev["lat"], prev["lon"], lat, lon)
                if dist < 1.0:
                    errors.append(f"WP{i}: Too close to WP{i-1} ({dist:.2f}m < 1m)")
    
    is_valid = len(errors) == 0
    return is_valid, errors


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two coordinates in meters (Haversine formula).
    
    Args:
        lat1, lon1: First coordinate (degrees)
        lat2, lon2: Second coordinate (degrees)
    
    Returns:
        Distance in meters
    """
    R = 6371000  # Earth radius in meters
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


__all__ = ["validate_waypoints", "calculate_distance"]

# Made with Bob
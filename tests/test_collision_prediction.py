"""
Tests for collision prediction module.

Tests the CollisionPredictor class and its integration with SafetyContext.
"""

import pytest
from droneresearch.safety.collision_predictor import (
    CollisionPredictor,
    CollisionPrediction,
    DroneState,
)


class TestDroneState:
    """Test DroneState dataclass."""

    def test_position_at_zero_velocity(self):
        """Drone with zero velocity stays in place."""
        state = DroneState(x=10, y=20, z=30, vx=0, vy=0, vz=0)
        pos = state.position_at(5.0)
        assert pos == (10, 20, 30)

    def test_position_at_with_velocity(self):
        """Drone moves according to velocity."""
        state = DroneState(x=0, y=0, z=10, vx=2, vy=1, vz=0.5)
        pos = state.position_at(5.0)
        assert pos == (10, 5, 12.5)

    def test_distance_to(self):
        """Calculate 3D distance between drones."""
        state1 = DroneState(x=0, y=0, z=0)
        state2 = DroneState(x=3, y=4, z=0)
        assert state1.distance_to(state2) == 5.0

    def test_distance_to_3d(self):
        """Calculate 3D distance with altitude difference."""
        state1 = DroneState(x=0, y=0, z=0)
        state2 = DroneState(x=0, y=0, z=10)
        assert state1.distance_to(state2) == 10.0


class TestCollisionPredictor:
    """Test CollisionPredictor class."""

    def test_no_collision_stationary_drones(self):
        """Stationary drones far apart have no collision."""
        predictor = CollisionPredictor(
            time_horizon=10.0,
            min_separation=2.0,
            sample_rate=0.5
        )
        
        states = {
            "D1": DroneState(x=0, y=0, z=10, vx=0, vy=0, vz=0, armed=True),
            "D2": DroneState(x=10, y=0, z=10, vx=0, vy=0, vz=0, armed=True),
        }
        
        predictions = predictor.predict(states)
        assert len(predictions) == 0

    def test_head_on_collision(self):
        """Two drones flying towards each other."""
        predictor = CollisionPredictor(
            time_horizon=10.0,
            min_separation=2.0,
            sample_rate=0.5
        )
        
        states = {
            "D1": DroneState(x=0, y=0, z=10, vx=2, vy=0, vz=0, armed=True),
            "D2": DroneState(x=20, y=0, z=10, vx=-2, vy=0, vz=0, armed=True),
        }
        
        predictions = predictor.predict(states)
        assert len(predictions) == 1
        
        pred = predictions[0]
        assert pred.drone_a == "D1"
        assert pred.drone_b == "D2"
        assert pred.time_to_collision > 0
        assert pred.time_to_collision < 10.0
        assert pred.min_distance < 2.0

    def test_perpendicular_paths_no_collision(self):
        """Drones on perpendicular paths that don't intersect."""
        predictor = CollisionPredictor(
            time_horizon=10.0,
            min_separation=2.0,
            sample_rate=0.5
        )
        
        states = {
            "D1": DroneState(x=0, y=0, z=10, vx=2, vy=0, vz=0, armed=True),
            "D2": DroneState(x=0, y=10, z=10, vx=0, vy=2, vz=0, armed=True),
        }
        
        predictions = predictor.predict(states)
        assert len(predictions) == 0

    def test_severity_levels(self):
        """Test severity classification."""
        predictor = CollisionPredictor(
            time_horizon=10.0,
            min_separation=2.0,
            sample_rate=0.1,
            critical_threshold=1.0,
            warning_threshold=1.5
        )
        
        # Critical: very close approach
        states_critical = {
            "D1": DroneState(x=0, y=0, z=10, vx=1, vy=0, vz=0, armed=True),
            "D2": DroneState(x=5, y=0, z=10, vx=-1, vy=0, vz=0, armed=True),
        }
        preds = predictor.predict(states_critical)
        assert len(preds) == 1
        assert preds[0].severity == "critical"
        assert preds[0].min_distance < 1.0

    def test_unarmed_drones_ignored(self):
        """Unarmed drones are not checked for collisions."""
        predictor = CollisionPredictor(
            time_horizon=10.0,
            min_separation=2.0,
            sample_rate=0.5
        )
        
        states = {
            "D1": DroneState(x=0, y=0, z=10, vx=2, vy=0, vz=0, armed=False),
            "D2": DroneState(x=10, y=0, z=10, vx=-2, vy=0, vz=0, armed=False),
        }
        
        predictions = predictor.predict(states)
        assert len(predictions) == 0

    def test_mixed_armed_unarmed(self):
        """Only armed pairs are checked."""
        predictor = CollisionPredictor(
            time_horizon=10.0,
            min_separation=2.0,
            sample_rate=0.5
        )
        
        # D1 and D2 would collide, but D2 is unarmed
        # D1 and D3 will collide (both armed)
        states = {
            "D1": DroneState(x=0, y=0, z=10, vx=2, vy=0, vz=0, armed=True),
            "D2": DroneState(x=10, y=0, z=10, vx=-2, vy=0, vz=0, armed=False),
            "D3": DroneState(x=10, y=0, z=10, vx=-2, vy=0, vz=0, armed=True),
        }
        
        predictions = predictor.predict(states)
        # Only D1-D3 collision (both armed)
        assert len(predictions) == 1
        assert set([predictions[0].drone_a, predictions[0].drone_b]) == {"D1", "D3"}

    def test_multiple_collisions(self):
        """Multiple collision pairs detected."""
        predictor = CollisionPredictor(
            time_horizon=10.0,
            min_separation=2.0,
            sample_rate=0.5
        )
        
        states = {
            "D1": DroneState(x=0, y=0, z=10, vx=2, vy=0, vz=0, armed=True),
            "D2": DroneState(x=10, y=0, z=10, vx=-2, vy=0, vz=0, armed=True),
            "D3": DroneState(x=0, y=10, z=10, vx=0, vy=-2, vz=0, armed=True),
            "D4": DroneState(x=0, y=20, z=10, vx=0, vy=2, vz=0, armed=True),
        }
        
        predictions = predictor.predict(states)
        # D1-D2 collision and D3-D4 collision
        assert len(predictions) == 2

    def test_predictions_sorted_by_time(self):
        """Predictions are sorted by time_to_collision."""
        predictor = CollisionPredictor(
            time_horizon=20.0,
            min_separation=2.0,
            sample_rate=0.5
        )
        
        # Two collision pairs with different times
        # Pair 1: D1-D2 horizontal collision (slower)
        # Pair 2: D3-D4 horizontal collision (faster)
        states = {
            "D1": DroneState(x=0, y=0, z=10, vx=1, vy=0, vz=0, armed=True),
            "D2": DroneState(x=30, y=0, z=10, vx=-1, vy=0, vz=0, armed=True),
            "D3": DroneState(x=0, y=10, z=10, vx=0, vy=2, vz=0, armed=True),
            "D4": DroneState(x=0, y=20, z=10, vx=0, vy=-2, vz=0, armed=True),
        }
        
        predictions = predictor.predict(states)
        assert len(predictions) == 2
        # D3-D4 collision happens sooner (faster approach: 10m at 4m/s vs 30m at 2m/s)
        assert predictions[0].time_to_collision < predictions[1].time_to_collision

    def test_collision_point_calculation(self):
        """Collision point is midpoint between drones at closest approach."""
        predictor = CollisionPredictor(
            time_horizon=10.0,
            min_separation=2.0,
            sample_rate=0.1
        )
        
        states = {
            "D1": DroneState(x=0, y=0, z=10, vx=1, vy=0, vz=0, armed=True),
            "D2": DroneState(x=10, y=0, z=10, vx=-1, vy=0, vz=0, armed=True),
        }
        
        predictions = predictor.predict(states)
        assert len(predictions) == 1
        
        # Collision point should be near (5, 0, 10) - midpoint
        point = predictions[0].collision_point
        assert 4.5 < point[0] < 5.5
        assert -0.5 < point[1] < 0.5
        assert 9.5 < point[2] < 10.5

    def test_to_dict_conversion(self):
        """CollisionPrediction converts to QML-friendly dict."""
        pred = CollisionPrediction(
            drone_a="D1",
            drone_b="D2",
            time_to_collision=5.5,
            min_distance=1.2,
            collision_point=(10.5, 20.3, 30.7),
            severity="warning"
        )
        
        d = pred.to_dict()
        assert d["droneA"] == "D1"
        assert d["droneB"] == "D2"
        assert d["timeToCollision"] == 5.5
        assert d["minDistance"] == 1.2
        assert d["collisionPoint"]["x"] == 10.5
        assert d["collisionPoint"]["y"] == 20.3
        assert d["collisionPoint"]["z"] == 30.7
        assert d["severity"] == "warning"

    def test_vertical_collision(self):
        """Drones on vertical collision course."""
        predictor = CollisionPredictor(
            time_horizon=10.0,
            min_separation=2.0,
            sample_rate=0.5
        )
        
        states = {
            "D1": DroneState(x=0, y=0, z=5, vx=0, vy=0, vz=1, armed=True),
            "D2": DroneState(x=0, y=0, z=15, vx=0, vy=0, vz=-1, armed=True),
        }
        
        predictions = predictor.predict(states)
        assert len(predictions) == 1
        assert predictions[0].min_distance < 2.0

    def test_time_horizon_limit(self):
        """Collisions beyond time horizon are not detected."""
        predictor = CollisionPredictor(
            time_horizon=5.0,  # Short horizon
            min_separation=2.0,
            sample_rate=0.5
        )
        
        # Slow approach - collision after 10 seconds
        states = {
            "D1": DroneState(x=0, y=0, z=10, vx=0.5, vy=0, vz=0, armed=True),
            "D2": DroneState(x=15, y=0, z=10, vx=-0.5, vy=0, vz=0, armed=True),
        }
        
        predictions = predictor.predict(states)
        # Collision happens at t=15s, beyond 5s horizon
        assert len(predictions) == 0


class TestCollisionPredictorEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_states(self):
        """Empty state dict returns no predictions."""
        predictor = CollisionPredictor()
        predictions = predictor.predict({})
        assert len(predictions) == 0

    def test_single_drone(self):
        """Single drone has no collisions."""
        predictor = CollisionPredictor()
        states = {
            "D1": DroneState(x=0, y=0, z=10, vx=1, vy=0, vz=0, armed=True),
        }
        predictions = predictor.predict(states)
        assert len(predictions) == 0

    def test_zero_velocity_collision(self):
        """Drones already too close with zero velocity."""
        predictor = CollisionPredictor(
            time_horizon=10.0,
            min_separation=2.0,
            sample_rate=0.5
        )
        
        states = {
            "D1": DroneState(x=0, y=0, z=10, vx=0, vy=0, vz=0, armed=True),
            "D2": DroneState(x=1, y=0, z=10, vx=0, vy=0, vz=0, armed=True),
        }
        
        predictions = predictor.predict(states)
        assert len(predictions) == 1
        assert predictions[0].time_to_collision == 0.0
        assert predictions[0].min_distance < 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob

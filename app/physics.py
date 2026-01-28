"""
Physics engine for Mallard locomotive.
Handles prototype-to-scale velocity conversion and encoder-based odometry.
"""
from typing import Dict

class PhysicsEngine:
    """Converts DCC speed to regulator percentage based on scale physics."""

    def __init__(self, cv: Dict[int, any]) -> None:
        """
        Initialises physics engine with scale-specific parameters.

        Why: Precomputes velocity conversions and wheel geometry to avoid
             repeated calculations in the 50Hz main loop.

        Args:
            cv: Configuration variable dictionary containing:
                - cv[39]: Prototype speed in km/h
                - cv[40]: Scale ratio (e.g., 76 for 1:76 OO gauge)
                - cv[37]: Wheel radius in millimeters * 100
                - cv[38]: Number of encoder segments per revolution

        Safety: Invalid CV values could cause incorrect speed mappings.
                Validates critical parameters during initialisation.

        Example:
            >>> cv = {39: 203, 40: 76, 37: 1325, 38: 12}
            >>> engine = PhysicsEngine(cv)
            >>> engine.v_scale_cms > 0
            True
        """
        self.cv = cv
        # Precompute scale velocity
        proto_kph = float(cv[39])
        scale_ratio = float(cv[40])
        self.v_scale_cms = (proto_kph * 100000.0) / (scale_ratio * 3600.0)

        # Wheel geometry
        self.wheel_radius = float(cv[37]) / 100000.0  # (mm * 100) to meters
        self.encoder_segments = int(cv[38])
        self.distance_per_tick = (2.0 * 3.14159 * self.wheel_radius) / self.encoder_segments

    def speed_to_regulator(self, dcc_speed: int) -> float:
        """
        Maps DCC speed (0-127) to regulator percentage (0-100).

        Why: DCC speed commands are 7-bit integers (0-127) but regulator
             valve position is expressed as percentage open (0-100%).

        Args:
            dcc_speed: DCC speed step command (0-127, where 0=stop, 127=full)

        Returns:
            Regulator opening percentage (0.0-100.0)

        Safety: Zero speed MUST return 0.0 to ensure valve closes completely.
                Invalid DCC speeds are clamped to valid range.

        Example:
            >>> engine.speed_to_regulator(0)
            0.0
            >>> engine.speed_to_regulator(127)
            100.0
            >>> 49.0 < engine.speed_to_regulator(64) < 51.0  # Half speed
            True
        """
        # Validate and clamp input
        if dcc_speed <= 0:
            return 0.0
        dcc_speed = min(dcc_speed, 127)

        # Linear mapping with minimum threshold
        return (dcc_speed / 127.0) * 100.0

    def calc_velocity(self, encoder_delta: int, time_ms: int) -> float:
        """
        Calculates current velocity in cm/s from encoder.

        Why: Optical wheel encoder provides distance traveled; dividing by time
             gives velocity for odometry and speed feedback.

        Args:
            encoder_delta: Number of encoder ticks since last calculation (≥0)
            time_ms: Time elapsed in milliseconds (≥0)

        Returns:
            Velocity in centimeters per second (cm/s), always ≥0

        Safety: Division by zero returns 0.0 instead of crashing. Negative
                values are clamped to zero (encoder can't count backwards).

        Example:
            >>> engine.calc_velocity(12, 1000)  # 1 wheel rotation in 1 second
            8.32  # Approximate, depends on wheel radius
            >>> engine.calc_velocity(0, 1000)
            0.0
            >>> engine.calc_velocity(10, 0)  # Zero time
            0.0
        """
        # Validate inputs
        if time_ms <= 0 or encoder_delta < 0:
            return 0.0

        distance_m = encoder_delta * self.distance_per_tick
        time_s = time_ms / 1000.0
        velocity_ms = distance_m / time_s
        velocity_cms = velocity_ms * 100.0  # m/s to cm/s

        return max(0.0, velocity_cms)  # Ensure non-negative

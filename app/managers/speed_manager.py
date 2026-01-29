"""
SpeedManager: Prototypical speed control for live steam locomotive.
"""
from typing import Any

class SpeedManager:
    """
    Manages speed and regulator/servo commands using prototypical control logic.

    Why:
        DCC speed sets the target speed. The regulator (throttle) is adjusted to accelerate or decelerate towards the target speed, not set directly. This mimics real locomotive operation, where the driver opens the regulator to accelerate and closes it to maintain speed.

    Args:
        actuators: Actuators interface (for servo, regulator)
        cv: Configuration variables (dict)
        speed_sensor: Callable returning current speed in cm/s

    Safety:
        Regulator is limited to 0-100%. Sudden changes are slew-rate limited elsewhere.
    """
    def __init__(self, actuators: Any, cv: dict, speed_sensor: Any):
        self.actuators = actuators
        self.cv = cv
        self.speed_sensor = speed_sensor
        self.target_speed = 0.0  # cm/s
        self._last_regulator = 0.0

    def set_speed(self, dcc_speed: float, direction: bool) -> None:
        """
        Sets the target speed or regulator position from DCC, depending on CV52.

        Why: Allows user to select between feedback speed control (cruise control) and direct throttle mode.

        Args:
            dcc_speed: DCC speed command (0-127, or as per protocol)
            direction: True for forward, False for reverse

        Returns:
            None

        Safety:
            Regulator is limited to 0-100%. Sudden changes are slew-rate limited elsewhere.

        Example:
            >>> sm.set_speed(64, True)
        """
        mode = self.cv.get("52", 1)  # CV52: 0=Direct throttle, 1=Feedback speed control (default)
        if mode == 0:
            # Direct throttle mode: DCC speed sets regulator directly
            regulator_percent = self._dcc_to_regulator(dcc_speed)
            self._last_regulator = regulator_percent
            self.actuators.set_regulator(regulator_percent, direction)
        else:
            # Feedback speed control (cruise control)
            self.target_speed = self._dcc_to_target_speed(dcc_speed)
            actual_speed = self.speed_sensor()
            regulator_percent = self._compute_regulator(actual_speed, self.target_speed)
            self._last_regulator = regulator_percent
            self.actuators.set_regulator(regulator_percent, direction)

    def _dcc_to_regulator(self, dcc_speed: float) -> float:
        """
        Converts DCC speed command to regulator percent (direct mapping).

        Why: Used in direct throttle mode (CV52=0).

        Args:
            dcc_speed: DCC speed command (0-127)

        Returns:
            Regulator percent (0.0-100.0)

        Safety:
            Clamped to 0-100%.

        Example:
            >>> _dcc_to_regulator(64)
            50.4
        """
        if not (0 <= dcc_speed <= 127):
            return 0.0
        return (dcc_speed / 127.0) * 100.0
        """
        Sets the target speed from DCC and updates regulator accordingly.

        Why: DCC speed is a command for desired speed, not throttle position.

        Args:
            dcc_speed: DCC speed command (0-127, or as per protocol)
            direction: True for forward, False for reverse

        Returns:
            None

        Safety:
            Regulator is limited to 0-100%. Sudden changes are slew-rate limited elsewhere.

        Example:
            >>> sm.set_speed(64, True)
        """
        self.target_speed = self._dcc_to_target_speed(dcc_speed)
        actual_speed = self.speed_sensor()
        regulator_percent = self._compute_regulator(actual_speed, self.target_speed)
        self._last_regulator = regulator_percent
        self.actuators.set_regulator(regulator_percent, direction)

    def _dcc_to_target_speed(self, dcc_speed: float) -> float:
        """
        Converts DCC speed command to target speed in cm/s using physics module.

        Why: Ensures correct scale speed for model.

        Args:
            dcc_speed: DCC speed command (0-127)

        Returns:
            Target speed in cm/s (float)

        Raises:
            ValueError: If dcc_speed is out of range

        Safety:
            Returns 0.0 for invalid input (fail-safe)

        Example:
            >>> _dcc_to_target_speed(64)
            25.0
        """
        if not (0 <= dcc_speed <= 127):
            return 0.0
        # Use physics module if available, else linear mapping (placeholder)
        try:
            from app.physics import dcc_speed_to_cms
            return dcc_speed_to_cms(dcc_speed, self.cv)
        except ImportError:
            # Fallback: map 0-127 to 0-50 cm/s
            return (dcc_speed / 127.0) * 50.0

    def _compute_regulator(self, actual_speed: float, target_speed: float) -> float:
        """
        Computes regulator (throttle) setting using proportional control.

        Why: Regulator is opened to accelerate towards target speed, closed as target is approached.

        Args:
            actual_speed: Current speed in cm/s
            target_speed: Desired speed in cm/s

        Returns:
            Regulator percent (0.0-100.0)

        Safety:
            Regulator is clamped to 0-100%. Sudden changes are slew-rate limited elsewhere.

        Example:
            >>> _compute_regulator(10.0, 20.0)
            50.0
        """
        error = target_speed - actual_speed
        k_p = self.cv.get("51", 2.0)  # CV51: Proportional gain (default 2.0)
        regulator = self._last_regulator + k_p * error
        # Clamp regulator to 0-100%
        return max(0.0, min(100.0, regulator))

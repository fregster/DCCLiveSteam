"""
Hardware abstraction interfaces for sensors and actuators.

Why: Enforces testable, safe, and maintainable hardware access patterns.
All hardware drivers must implement these interfaces.

British English spelling and terminology is used throughout.
"""
from abc import ABC, abstractmethod
from typing import Any

class ISensor(ABC):
    """
    Abstract interface for all hardware sensors.

    Why:
        Ensures all sensor access is testable and encapsulated for safety-critical systems.

    Args:
        None (interface only)

    Returns:
        None (interface only)

    Raises:
        NotImplementedError: If not implemented in subclass.

    Safety:
        All hardware access must be encapsulated to prevent unsafe direct access.

    Example:
        class TempSensor(ISensor):
            def read(self):
                return 42.0
    """
    @abstractmethod
    def read(self) -> Any:
        """
        Reads the current value from the sensor.

        Why:
            Provides a unified method for sensor value retrieval, enabling testability and safety checks.

        Args:
            None

        Returns:
            Any: The current sensor value (type depends on sensor).

        Raises:
            Exception: If sensor read fails or is unsafe.

        Safety:
            Must raise on unsafe or out-of-range values to trigger system safety shutdown.

        Example:
            >>> temp = sensor.read()
        """
        # Interface method; must be implemented by subclass
        raise NotImplementedError()

    def health(self) -> bool:
        """
        Checks if the sensor is healthy and readings are valid.

        Why:
            Enables runtime health monitoring for graceful degradation and safety.

        Args:
            None

        Returns:
            bool: True if sensor is healthy, False otherwise.

        Raises:
            None

        Safety:
            Should be used to trigger degraded mode or shutdown if False.

        Example:
            >>> if not sensor.health():
            ...     system.enter_degraded_mode()
        """
        return True

class IActuator(ABC):
    """
    Abstract interface for all hardware actuators.

    Why:
        Ensures all actuator control is testable and encapsulated for safety-critical systems.

    Args:
        None (interface only)

    Returns:
        None (interface only)

    Raises:
        NotImplementedError: If not implemented in subclass.

    Safety:
        All hardware access must be encapsulated to prevent unsafe direct access.

    Example:
        class Servo(IActuator):
            def set(self, value):
                raise NotImplementedError()
    """
    @abstractmethod
    def set(self, value: Any) -> None:
        """
        Sets the actuator to the specified value.

        Why:
            Provides a unified method for actuator control, enabling testability and safety checks.

        Args:
            value: The value to set (type depends on actuator).

        Returns:
            None

        Raises:
            Exception: If actuator command fails or is unsafe.

        Safety:
            Must raise on unsafe or out-of-range values to trigger system safety shutdown.

        Example:
            >>> servo.set(50)
        """
        # Interface method; must be implemented by subclass
        raise NotImplementedError()

    def status(self) -> Any:
        """
        Returns the current status or feedback from the actuator.

        Why:
            Enables runtime feedback and monitoring for safety and diagnostics.

        Args:
            None

        Returns:
            Any: The current status or feedback value (type depends on actuator).

        Raises:
            None

        Safety:
            Should be used to verify actuator state and trigger diagnostics if abnormal.

        Example:
            >>> status = servo.status()
        """
        return None

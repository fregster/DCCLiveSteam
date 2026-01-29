"""
Heater control module for live steam locomotive (ESP32 TinyPICO).

Provides:
- BoilerHeaterPWM: PWM control for boiler heater (Tender, GPIO 25)
- SuperheaterHeaterPWM: PWM control for superheater (Tender, GPIO 26)
- HeaterActuators: Composite interface for both heaters

British English spelling and terminology enforced.
"""
import time
from machine import Pin, PWM

class BoilerHeaterPWM:
    """
    Controls boiler heater element via PWM output (Tender, GPIO 25).

    Why:
        Boiler pressure must be maintained for safe steam generation. PWM allows precise power control.

    Args:
        pin: PWM-capable pin number for boiler heater (default: 25)

    Returns:
        None

    Raises:
        None

    Safety:
        Duty cycle is clamped to 0-1023. On error, heater is forced OFF.

    Example:
        >>> boiler = BoilerHeaterPWM()
        >>> boiler.set_duty(800)
        >>> boiler.off()
    """
    def __init__(self, pin: int = 25) -> None:
        self.pwm = PWM(Pin(pin), freq=5000)
        self.duty = 0
        self.off()

    def set_duty(self, value: int) -> None:
        """
        Set boiler heater PWM duty cycle (0-1023).

        Args:
            value: Duty cycle (0-1023)

        Returns:
            None

        Raises:
            ValueError: If value is out of range

        Safety:
            Clamps value to 0-1023. On error, heater is forced OFF.

        Example:
            >>> boiler.set_duty(900)
        """
        if not (0 <= value <= 1023):
            self.off()
            raise ValueError(f"Boiler heater duty {value} out of range 0-1023")
        self.duty = value
        self.pwm.duty(value)

    def off(self) -> None:
        """
        Turn boiler heater OFF (duty=0).

        Args:
            None

        Returns:
            None

        Raises:
            None

        Safety:
            Always safe to call. Forces heater OFF.

        Example:
            >>> boiler.off()
        """
        self.duty = 0
        self.pwm.duty(0)


class SuperheaterHeaterPWM:
    """
    Controls superheater element via PWM output (Tender, GPIO 26).

    Why:
        Superheater temperature must be managed to avoid pipe damage and ensure dry steam. PWM allows staged warm-up and rapid response.

    Args:
        pin: PWM-capable pin number for superheater heater (default: 26)

    Returns:
        None

    Raises:
        None

    Safety:
        Duty cycle is clamped to 0-1023. On error, heater is forced OFF.

    Example:
        >>> superheater = SuperheaterHeaterPWM()
        >>> superheater.set_duty(256)
        >>> superheater.off()
    """
    def __init__(self, pin: int = 26) -> None:
        self.pwm = PWM(Pin(pin), freq=5000)
        self.duty = 0
        self.off()

    def set_duty(self, value: int) -> None:
        """
        Set superheater PWM duty cycle (0-1023).

        Args:
            value: Duty cycle (0-1023)

        Returns:
            None

        Raises:
            ValueError: If value is out of range

        Safety:
            Clamps value to 0-1023. On error, heater is forced OFF.

        Example:
            >>> superheater.set_duty(400)
        """
        if not (0 <= value <= 1023):
            self.off()
            raise ValueError(f"Superheater duty {value} out of range 0-1023")
        self.duty = value
        self.pwm.duty(value)

    def off(self) -> None:
        """
        Turn superheater OFF (duty=0).

        Args:
            None

        Returns:
            None

        Raises:
            None

        Safety:
            Always safe to call. Forces heater OFF.

        Example:
            >>> superheater.off()
        """
        self.duty = 0
        self.pwm.duty(0)


class HeaterActuators:
    """
    Composite interface for boiler and superheater heaters.

    Why:
        Allows coordinated control and staged logic (e.g., staged superheater warm-up based on pressure).

    Args:
        boiler_pin: GPIO for boiler heater (default: 25)
        superheater_pin: GPIO for superheater heater (default: 26)

    Returns:
        None

    Raises:
        None

    Safety:
        All safety logic of individual actuators applies. Use this class for coordinated shutdown.

    Example:
        >>> heaters = HeaterActuators()
        >>> heaters.set_boiler_duty(900)
        >>> heaters.set_superheater_duty(256)
        >>> heaters.all_off()
    """
    def __init__(self, boiler_pin: int = 25, superheater_pin: int = 26) -> None:
        self.boiler = BoilerHeaterPWM(boiler_pin)
        self.superheater = SuperheaterHeaterPWM(superheater_pin)

    def set_boiler_duty(self, value: int) -> None:
        self.boiler.set_duty(value)

    def set_superheater_duty(self, value: int) -> None:
        self.superheater.set_duty(value)

    def all_off(self) -> None:
        self.boiler.off()
        self.superheater.off()

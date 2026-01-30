"""
Boiler heater PWM control for live steam locomotive (ESP32 TinyPICO).

British English spelling and terminology enforced.
"""
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

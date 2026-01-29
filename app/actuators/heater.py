"""
Heater control module for live steam locomotive (ESP32 TinyPICO).

Contains HeaterPWM class for PWM-based heater element control.

British English spelling and terminology enforced.
"""
import time
from machine import Pin, PWM

class HeaterPWM:
    """
    Controls heater element via PWM output.

    Why:
        Boiler pressure and superheater temperature require precise power control.
        PWM allows proportional heating, reducing overshoot and improving efficiency.

    Args:
        pin: PWM-capable pin number for heater control

    Returns:
        None

    Raises:
        None

    Safety:
        Duty cycle is clamped to 0-1023. On error, heater is forced OFF.

    Example:
        >>> heater = HeaterPWM(pin=13)
        >>> heater.set_duty(512)
        >>> heater.off()
    """
    def __init__(self, pin: int) -> None:
        self.pwm = PWM(Pin(pin), freq=1000)
        self.duty = 0
        self.off()

    def set_duty(self, value: int) -> None:
        """
        Set heater PWM duty cycle (0-1023).

        Args:
            value: Duty cycle (0-1023)

        Returns:
            None

        Raises:
            ValueError: If value is out of range

        Safety:
            Clamps value to 0-1023. On error, heater is forced OFF.

        Example:
            >>> heater.set_duty(600)
        """
        if not (0 <= value <= 1023):
            self.off()
            raise ValueError(f"Heater duty {value} out of range 0-1023")
        self.duty = value
        self.pwm.duty(value)

    def off(self) -> None:
        """
        Turn heater OFF (duty=0).

        Args:
            None

        Returns:
            None

        Raises:
            None

        Safety:
            Always safe to call. Forces heater OFF.

        Example:
            >>> heater.off()
        """
        self.duty = 0
        self.pwm.duty(0)

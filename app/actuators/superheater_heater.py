"""
Superheater PWM control for live steam locomotive (ESP32 TinyPICO).

British English spelling and terminology enforced.
"""
from machine import Pin, PWM

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

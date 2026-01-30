"""
LED indicator classes for system status and diagnostics.

Contains:
    - GreenStatusLED: System status (boot, ready, DCC, motion)
    - FireboxLED: Error and warning indication
"""
import time
from typing import Optional, Any
from app.hardware_interfaces import IActuator

class GreenStatusLED(IActuator):
    """
    Status LED controller for system state indication (boot, ready, DCC, motion).
    ...existing docstring from actuators.py...
    """
    def __init__(self, led_hw: Any):
        """
        Args:
            led_hw: Hardware abstraction implementing set(value: bool)
        """
        self.led_hw = led_hw
        self.state = 'off'  # 'off', 'boot', 'solid', 'dcc_blink', 'moving'
        self.last_update = time.ticks_ms()
        self.blink_start = 0
        self.blinking = False
        self.dcc_blink_pending = False
        self.dcc_blink_time = 0

    def boot_flash(self) -> None:
        """Sets the LED to boot flashing mode (slow 1Hz flash). ...existing docstring..."""
        self.state = 'boot'

    def solid(self) -> None:
        """Sets the LED to solid ON mode (ready/normal operation). ...existing docstring..."""
        self.state = 'solid'

    def dcc_blink(self) -> None:
        """Triggers a short blink to indicate DCC packet received. ...existing docstring..."""
        self.dcc_blink_pending = True
        self.dcc_blink_time = time.ticks_ms()

    def moving_flash(self) -> None:
        """Sets the LED to rapid flash mode (4Hz) to indicate motion. ...existing docstring..."""
        self.state = 'moving'

    def off(self) -> None:
        """Turns the LED off. ...existing docstring..."""
        self.state = 'off'
        self._set_led(False)

    def update(self) -> None:
        """Updates the LED state based on the current mode. ...existing docstring..."""
        now = time.ticks_ms()
        if self.state == 'moving':
            if (now // 125) % 2 == 0:
                self._set_led(True)
            else:
                self._set_led(False)
        elif self.dcc_blink_pending:
            if time.ticks_diff(now, self.dcc_blink_time) < 100:
                self._set_led(True)
            else:
                self._set_led(False)
                self.dcc_blink_pending = False
        elif self.state == 'boot':
            if (now // 500) % 2 == 0:
                self._set_led(True)
            else:
                self._set_led(False)
        elif self.state == 'solid':
            self._set_led(True)
        else:
            self._set_led(False)

    def _set_led(self, on: bool) -> None:
        """Sets the LED output state via hardware abstraction."""
        self.led_hw.set(on)

    def set(self, value: Any) -> None:
        """Implements IActuator interface."""
        self._set_led(bool(value))

    def status(self) -> Any:
        return self.state


# --- Status LED Manager (from status_led.py) ---
from typing import Any

class StatusLEDManager:
    """
    Manages the green status LED for system state indication.

    Args:
        green_led: GreenStatusLED instance
    """
    def __init__(self, green_led: Any):
        self.green_led = green_led
        self.last_motion = False
        self.last_ready = False

    def update(self, motion: bool, ready: bool) -> None:
        """
        Updates the LED state based on motion and ready state.
        """
        if motion:
            self.green_led.moving_flash()
        elif ready:
            self.green_led.solid()
        else:
            self.green_led.off()
        self.green_led.update()

class FireboxLED(IActuator):
    """
    Firebox LED controller for error and warning indication.
    ...existing docstring from actuators.py...
    """
    def __init__(self, led_hw: Any, red_duty: int = 1023, orange_duty: int = 512):
        """
        Args:
            led_hw: Hardware abstraction implementing set(value: bool, colour: Optional[str])
        """
        self.led_hw = led_hw
        self.red_duty = red_duty
        self.orange_duty = orange_duty
        self.state = 'off'  # 'off', 'red', 'orange', 'flash_red', 'flash_orange'
        self.last_update = time.ticks_ms()
        self.flash_count = 0
        self.flash_total = 0
        self.flash_on = False
        self.solid_start = 0
        self.code = 0

    def set_error(self, code: int):
        """
        Set error state: solid red for 5s, then flash red N times (N=code).
        Repeat if error persists.
        ...existing docstring...
        """
        self.state = 'red'
        self.code = code
        self.solid_start = time.ticks_ms()
        self.flash_count = 0
        self.flash_total = code
        self.flash_on = False

    def set_warning(self, code: int):
        """
        Set warning state: solid orange for 5s, then flash orange N times (N=code).
        Repeat if warning persists.
        ...existing docstring...
        """
        if self.state != 'red':
            self.state = 'orange'
            self.code = code
            self.solid_start = time.ticks_ms()
            self.flash_count = 0
            self.flash_total = code
            self.flash_on = False

    def clear(self):
        """Clear any error/warning, turn LED off. ...existing docstring..."""
        self.state = 'off'
        self._set_led(False)

    def update(self):
        """Call in main loop to update LED state (non-blocking). ...existing docstring..."""
        now = time.ticks_ms()
        if self.state == 'red':
            if time.ticks_diff(now, self.solid_start) < 5000:
                self._set_led(True, 'red')
            else:
                self._flash('red')
        elif self.state == 'orange':
            if time.ticks_diff(now, self.solid_start) < 5000:
                self._set_led(True, 'orange')
            else:
                self._flash('orange')
        else:
            self._set_led(False)

    def _flash(self, colour: str):
        """Flashes the LED in a pattern corresponding to the code. ...existing docstring..."""
        now = time.ticks_ms()
        period = 800
        on_time = 400
        elapsed = time.ticks_diff(now, self.solid_start + 5000)
        flash_index = int(elapsed // period)
        in_flash = flash_index < self.flash_total
        phase = elapsed % period
        if in_flash:
            if phase < on_time:
                self._set_led(True, colour)
            else:
                self._set_led(False)
        else:
            self.solid_start = now
            self.flash_count = 0
            self._set_led(True, colour)

    def _set_led(self, on: bool, colour: Optional[str] = None):
        """Sets the LED output state via hardware abstraction."""
        self.led_hw.set(on, colour)

    def set(self, value: Any) -> None:
        """Implements IActuator interface. Accepts (on, colour) tuple or bool."""
        if isinstance(value, tuple):
            on, colour = value
        else:
            on, colour = bool(value), None
        self._set_led(on, colour)

    def status(self) -> Any:
        return self.state

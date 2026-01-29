"""
StatusLEDManager: High-level status LED state machine for locomotive.

Why:
    Encapsulates all logic for updating the green status LED based on motion, ready state, and other system events.
    Keeps main.py free of LED state logic and makes LED behaviour testable.

Usage:
    status_led = StatusLEDManager(green_led)
    status_led.update(motion_state, ready_state)
"""
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

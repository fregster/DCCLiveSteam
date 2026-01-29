"""
PressureControlManager: Handles periodic pressure control updates.

Why:
    Encapsulates timing and update logic for pressure control, keeping main.py simple.
    Ensures pressure.update() is called at the correct interval.

Usage:
    pressure_manager = PressureControlManager(pressure)
    pressure_manager.process(pressure_value)
"""
import time
from typing import Any

class PressureControlManager:
    """
    Manages periodic pressure control updates.

    Args:
        pressure: PressureController instance
        interval_ms: Update interval in milliseconds (default 500ms)
    """
    def __init__(self, pressure: Any, interval_ms: int = 500):
        self.pressure = pressure
        self.interval_ms = interval_ms
        self.last_update = time.ticks_ms()

    def process(self, pressure_value: float) -> None:
        """
        Calls pressure.update() if interval has elapsed.
        """
        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_update) > self.interval_ms:
            dt = time.ticks_diff(now, self.last_update) / 1000.0
            self.pressure.update(pressure_value, dt)
            self.last_update = now

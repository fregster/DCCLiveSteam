"""
TelemetryManager: Handles BLE telemetry queueing and sending.
"""
from ..ble_uart import BLE_UART
from typing import Any, Tuple

class TelemetryManager:
    """
    Handles BLE telemetry queueing and sending.
    Args:
        ble: BLE_UART instance
        actuators: Actuators interface (for servo current, etc.)
    """
    def __init__(self, ble: Any, actuators: Any, status_reporter=None):
        self.ble = ble
        self.actuators = actuators
        self.status_reporter = status_reporter
        self.last_queued = None
        self._last_periodic = None

    def queue_telemetry(self, velocity_cms: float, pressure: float, temps: Tuple[float, float, float]) -> None:
        servo_current = int(getattr(self.actuators, 'servo_current', 0))
        self.ble.send_telemetry(velocity_cms, pressure, temps, servo_current)
        self.last_queued = (velocity_cms, pressure, temps, servo_current)

    def process(self) -> None:
        self.ble.process_telemetry()

    def process_periodic(self, velocity_cms: float, pressure: float, temps: Tuple[float, float, float], servo_current: float, loop_count: int, now_ms: int = None) -> None:
        import time
        if now_ms is None:
            now_ms = time.ticks_ms()
        if self._last_periodic is None:
            self._last_periodic = now_ms
        if time.ticks_diff(now_ms, self._last_periodic) > 1000:
            self.queue_telemetry(velocity_cms, pressure, temps)
            if self.status_reporter:
                self.status_reporter.process(
                    velocity_cms, pressure, temps, servo_current, loop_count
                )
            self._last_periodic = now_ms

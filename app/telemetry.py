"""
TelemetryManager: BLE telemetry queueing and sending subsystem.

Why:
    Encapsulates all BLE telemetry formatting, queueing, and sending logic.
    Provides a simple interface for the main loop to update and send telemetry.

Usage:
    telemetry = TelemetryManager(ble, mech)
    telemetry.queue_telemetry(...)
    telemetry.process()
"""
from typing import Tuple, Any

class TelemetryManager:
    """
    Handles BLE telemetry queueing and sending.

    Args:
        ble: BLE_UART instance
        mech: MechanicalMapper instance (for servo current)
    """
    def __init__(self, ble: Any, mech: Any, status_reporter=None):
        self.ble = ble
        self.mech = mech
        self.status_reporter = status_reporter
        self.last_queued = None
        self._last_periodic = None

    def queue_telemetry(self, velocity_cms: float, pressure: float, temps: Tuple[float, float, float]) -> None:
        """
        Queues a telemetry packet for BLE transmission.
        """
        servo_current = int(getattr(self.mech, 'current', 0))
        self.ble.send_telemetry(velocity_cms, pressure, temps, servo_current)
        self.last_queued = (velocity_cms, pressure, temps, servo_current)

    def process(self) -> None:
            def process_periodic(self, velocity_cms: float, pressure: float, temps: Tuple[float, float, float], servo_current: float, loop_count: int, now_ms: int = None) -> None:
                """
                Handles periodic (1s) telemetry and status reporting.
                Should be called every loop with current values.
                """
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
        """
        Sends any queued telemetry packet (non-blocking).
        """
        self.ble.process_telemetry()

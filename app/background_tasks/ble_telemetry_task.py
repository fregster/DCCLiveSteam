"""
Background task for non-blocking BLE telemetry transmission.
"""
import time

class BLETelemetryTask:
    """
    Handles periodic, non-blocking BLE telemetry transmission.
    """
    def __init__(self, ble, interval_ms=1000):
        self.ble = ble
        self.interval_ms = interval_ms
        self.last_telemetry = time.ticks_ms()
        self._pending_args = None

    def queue_telemetry(self, speed, psi, temps, servo_duty):
        self._pending_args = (speed, psi, temps, servo_duty)

    def process(self):
        now = time.ticks_ms()
        # If interval_ms is 0, always send immediately (for testability)
        if self._pending_args and (self.interval_ms == 0 or time.ticks_diff(now, self.last_telemetry) > self.interval_ms):
            speed, psi, temps, servo_duty = self._pending_args
            self.ble.send_telemetry(speed, psi, temps, servo_duty)
            self.last_telemetry = now
            self._pending_args = None
        self.ble.process_telemetry()

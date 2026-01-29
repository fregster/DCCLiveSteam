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
    def __init__(self, ble: Any, mech: Any):
        self.ble = ble
        self.mech = mech
        self.last_queued = None

    def queue_telemetry(self, velocity_cms: float, pressure: float, temps: Tuple[float, float, float]) -> None:
        """
        Queues a telemetry packet for BLE transmission.
        """
        servo_current = int(getattr(self.mech, 'current', 0))
        self.ble.send_telemetry(velocity_cms, pressure, temps, servo_current)
        self.last_queued = (velocity_cms, pressure, temps, servo_current)

    def process(self) -> None:
        """
        Sends any queued telemetry packet (non-blocking).
        """
        self.ble.process_telemetry()

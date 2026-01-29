"""
Unit tests for TelemetryManager (app/telemetry.py)
"""
from app.telemetry import TelemetryManager
from unittest.mock import MagicMock

def test_queue_telemetry():
    ble = MagicMock()
    mech = MagicMock(current=123)
    tm = TelemetryManager(ble, mech)
    tm.queue_telemetry(10.0, 1.0, (100.0, 200.0, 50.0))
    ble.send_telemetry.assert_called_with(10.0, 1.0, (100.0, 200.0, 50.0), 123)

def test_process_calls_ble():
    ble = MagicMock()
    mech = MagicMock()
    tm = TelemetryManager(ble, mech)
    tm.process()
    ble.process_telemetry.assert_called()
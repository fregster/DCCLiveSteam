"""
Unit tests for PressureControlManager (app/pressure_manager.py)
"""
import time
from app.pressure_manager import PressureControlManager
from unittest.mock import MagicMock

def test_process_calls_update(monkeypatch):
    pressure = MagicMock()
    manager = PressureControlManager(pressure, interval_ms=1)
    # Fast-forward time
    monkeypatch.setattr(time, 'ticks_ms', lambda: 1000)
    manager.last_update = 0
    manager.process(42.0)
    pressure.update.assert_called()
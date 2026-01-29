"""
Unit tests for PowerManager (app/managers/power_manager.py)
"""
import pytest
from unittest.mock import MagicMock
from app.managers.power_manager import PowerManager

class DummyLoco:
    def __init__(self):
        self.cv = {51: 4.5}
        self.pressure = MagicMock()
        self.pressure.boiler_heater = MagicMock(_duty=1023)
        self.pressure.super_heater = MagicMock(_duty=1023)
        self.mech = MagicMock(current=100, target=0)
        self.log_event = MagicMock()
        self.die = MagicMock()
        self.safety_shutdown = MagicMock()

@pytest.fixture
def dummy_loco():
    return DummyLoco()

def test_estimate_total_current(dummy_loco):
    pm = PowerManager(dummy_loco, {})
    amps = pm.estimate_total_current()
    assert amps > 0

def test_process_overcurrent_triggers_die(dummy_loco):
    pm = PowerManager(dummy_loco, {})
    dummy_loco.pressure.boiler_heater._duty = 1023
    dummy_loco.pressure.super_heater._duty = 1023
    dummy_loco.mech.current = 100
    dummy_loco.mech.target = 0
    pm.power_budget_amps = 0.1  # Force overcurrent
    pm.process()
    dummy_loco.safety_shutdown.assert_called()
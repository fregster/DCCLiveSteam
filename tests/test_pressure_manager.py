
import pytest
from app.managers.pressure_manager import PressureManager
from unittest.mock import MagicMock

class DummyHeaterActuators:
    def __init__(self):
        self.boiler_duty = 0
        self.superheater_duty = 0
        self.all_off_called = False
    def set_boiler_duty(self, value):
        self.boiler_duty = value
    def set_superheater_duty(self, value):
        self.superheater_duty = value
    def all_off(self):
        self.all_off_called = True

def test_superheater_staged_logic():
    cv = {33: 40.0, 35: 60.0, 43: 250}
    heaters = DummyHeaterActuators()
    pm = PressureManager(heaters, cv)
    # Low pressure: superheater OFF
    pm.process(2.0, 0, 50.0, 0.1)
    assert heaters.superheater_duty == 0
    # 25% stage
    pm.process(15.0, 0, 50.0, 0.1)
    assert abs(heaters.superheater_duty - int(0.25 * 1023)) < 5
    # 50% stage
    pm.process(30.0, 0, 50.0, 0.1)
    assert abs(heaters.superheater_duty - int(0.5 * 1023)) < 5
    # 70%+temp control
    pm.process(39.0, 0, 200.0, 0.1)
    assert heaters.superheater_duty > int(0.5 * 1023)
    # Over temp: fallback to 30%
    pm.process(40.0, 0, 260.0, 0.1)
    assert abs(heaters.superheater_duty - int(0.3 * 1023)) < 5

def test_superheater_blowdown_spike():
    cv = {33: 40.0, 35: 60.0, 43: 250}
    heaters = DummyHeaterActuators()
    pm = PressureManager(heaters, cv)
    # Simulate regulator opening (spike starts)
    pm.process(40.0, 1, 200.0, 0.1)
    assert heaters.superheater_duty == 1023
    # Spike timer should decrement but still active
    pm.process(40.0, 0, 200.0, 0.5)
    assert heaters.superheater_duty == 1023
    # After spike duration (just over 1.0s), should drop
    pm.process(40.0, 0, 200.0, 0.5)  # total dt = 1.1s > 1.0s
    assert heaters.superheater_duty < 1023

def test_pressure_manager_shutdown():
    cv = {33: 40.0, 35: 60.0, 43: 250}
    heaters = DummyHeaterActuators()
    pm = PressureManager(heaters, cv)
    pm.shutdown()
    assert heaters.all_off_called
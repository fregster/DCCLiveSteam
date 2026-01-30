from unittest.mock import MagicMock
def test_pressure_manager_actuator_calls():
    """
    Test that PressureManager calls actuators with correct boiler and superheater duty values (mocked).
    """
    actuators = MagicMock()
    cv = {33: 20.0, 35: 30.0, 43: 250}
    pm = PressureManager(actuators, cv)
    pm.process(current_psi=10.0, regulator_open=0, superheater_temp=50.0, dt=0.1)
    assert actuators.set_boiler_duty.called
    assert actuators.set_superheater_duty.called

def test_pressure_manager_fallback_temp_only():
    """
    Test fallback mode: pressure sensor unavailable, uses temp-only safety logic (mocked).
    """
    actuators = MagicMock()
    cv = {33: 20.0, 35: 30.0, 43: 250}
    pm = PressureManager(actuators, cv)
    pm.pressure_sensor_available = False
    # Superheater temp below limit-10: boiler ON, superheater ON
    pm.process(current_psi=0, regulator_open=0, superheater_temp=200.0, dt=0.1)
    actuators.set_boiler_duty.assert_called_with(int(0.3 * 1023))
    actuators.set_superheater_duty.assert_called_with(int(0.25 * 1023))
    # Superheater temp above limit: both OFF
    pm.process(current_psi=0, regulator_open=0, superheater_temp=260.0, dt=0.1)
    actuators.set_boiler_duty.assert_called_with(0)
    actuators.set_superheater_duty.assert_called_with(0)

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
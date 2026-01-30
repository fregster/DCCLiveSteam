"""
Unit tests for PowerManager (app/managers/power_manager.py)
"""
import pytest
from unittest.mock import MagicMock
from app.managers.power_manager import PowerManager


# Mock Actuators interface for PowerManager tests
class DummyActuators:
    def __init__(self):
        self.boiler_pwm = 1023
        self.superheater_pwm = 1023
        self.servo_current = 100
        self.servo_target = 0
        self.set_boiler_duty_called = False
        self.set_superheater_duty_called = False
        self.set_servo_idle_called = False
        self.safety_shutdown_called = False
    def set_boiler_duty(self, value):
        self.boiler_pwm = value
        self.set_boiler_duty_called = True
    def set_superheater_duty(self, value):
        self.superheater_pwm = value
        self.set_superheater_duty_called = True
    def set_servo_idle(self):
        self.set_servo_idle_called = True
    def safety_shutdown(self, cause):
        self.safety_shutdown_called = True



@pytest.fixture
def dummy_actuators():
    return DummyActuators()

def test_estimate_total_current(dummy_actuators):
    pm = PowerManager(dummy_actuators, {})
    amps = pm.estimate_total_current()
    assert amps > 0

def test_process_overcurrent_triggers_safety_shutdown(dummy_actuators):
    pm = PowerManager(dummy_actuators, {})
    dummy_actuators.boiler_pwm = 1023
    dummy_actuators.superheater_pwm = 1023
    dummy_actuators.servo_current = 100
    dummy_actuators.servo_target = 0
    pm.power_budget_amps = 0.1  # Force overcurrent
    pm.process()
    assert dummy_actuators.safety_shutdown_called
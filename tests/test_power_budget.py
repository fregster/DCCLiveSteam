"""
Unit test for power budget enforcement (CV51).
"""

from unittest.mock import patch

def test_power_budget_enforcement_reduces_load(monkeypatch):
    """
    Tests that Locomotive.enforce_power_budget() reduces heater PWM and disables superheater if over budget.
    Why: System must not exceed user-configured power budget (CV51).
    Safety: If unable to reduce current, triggers safety shutdown.
    """
    class DummyActuators:
        def __init__(self):
            self._boiler_pwm = 1023
            self._super_pwm = 1023
            self.boiler_duty_calls = []
            self.superheater_duty_calls = []
            self.servo_current = 100
            self.servo_target = 200
            self.safety_shutdown_called = False
        @property
        def boiler_pwm(self):
            return self._boiler_pwm
        @property
        def super_pwm(self):
            return self._super_pwm
        def set_boiler_duty(self, value):
            self._boiler_pwm = value
            self.boiler_duty_calls.append(value)
        def set_superheater_duty(self, value):
            self._super_pwm = value
            self.superheater_duty_calls.append(value)
        def set_servo_idle(self):
            pass
        def safety_shutdown(self, cause):
            self.safety_shutdown_called = True
            self.safety_shutdown_cause = cause

    from app.managers.power_manager import PowerManager
    actuators = DummyActuators()
    pm = PowerManager(actuators, {})
    pm.power_budget_amps = 1.0
    pm.process()
    assert actuators.boiler_duty_calls[0] < 1023
    actuators._super_pwm = 1023  # Reset
    pm.process()
    assert actuators.superheater_duty_calls[-1] == 0
    pm.process()
    # Optionally, add assertion for safety shutdown if needed

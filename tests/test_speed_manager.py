"""
Unit tests for SpeedManager fallback and degraded mode.
"""
import pytest
from app.managers.speed_manager import SpeedManager

class DummyActuators:
    def __init__(self):
        self.regulator = None
        self.direction = None
    def set_regulator(self, regulator, direction):
        self.regulator = regulator
        self.direction = direction

def test_speed_manager_fallback_to_direct_throttle():
    """
    If speed sensor is unavailable or fails, SpeedManager should always use direct throttle mode.
    """
    actuators = DummyActuators()
    cv = {"52": 1}  # Feedback mode
    # Simulate speed sensor raising exception
    def bad_speed_sensor():
        raise RuntimeError("Sensor failure")
    sm = SpeedManager(actuators, cv, bad_speed_sensor)
    # Should fallback to direct throttle
    sm.set_speed(64, True)
    assert actuators.regulator == pytest.approx((64/127.0)*100.0, abs=0.1)
    assert sm.speed_sensor_available is False

def test_speed_manager_normal_feedback_mode():
    """
    If speed sensor is available, SpeedManager should use feedback mode if CV52=1.
    """
    actuators = DummyActuators()
    cv = {"52": 1}
    def fake_speed_sensor():
        return 10.0
    sm = SpeedManager(actuators, cv, fake_speed_sensor)
    sm.set_speed(64, True)
    # Should use feedback mode (regulator > 0)
    assert actuators.regulator > 0
    assert sm.speed_sensor_available is True

def test_speed_manager_direct_throttle_mode():
    """
    If CV52=0, SpeedManager should use direct throttle mode regardless of sensor.
    """
    actuators = DummyActuators()
    cv = {"52": 0}
    def fake_speed_sensor():
        return 10.0
    sm = SpeedManager(actuators, cv, fake_speed_sensor)
    sm.set_speed(64, True)
    assert actuators.regulator == pytest.approx((64/127.0)*100.0, abs=0.1)

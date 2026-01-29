import pytest
from unittest.mock import MagicMock, patch
from app.actuators.heater import HeaterPWM

class DummyPWM:
    def __init__(self, pin, freq=1000):
        self.pin = pin
        self.freq = freq
        self._duty = 0
    def duty(self, value):
        self._duty = value

@patch('app.actuators.heater.PWM', DummyPWM)
@patch('app.actuators.heater.Pin', MagicMock)
def test_heater_pwm_init_sets_duty_zero():
    heater = HeaterPWM(pin=13)
    assert heater.duty == 0
    assert heater.pwm._duty == 0

@patch('app.actuators.heater.PWM', DummyPWM)
@patch('app.actuators.heater.Pin', MagicMock)
def test_heater_pwm_set_duty_valid():
    heater = HeaterPWM(pin=13)
    heater.set_duty(512)
    assert heater.duty == 512
    assert heater.pwm._duty == 512

@patch('app.actuators.heater.PWM', DummyPWM)
@patch('app.actuators.heater.Pin', MagicMock)
def test_heater_pwm_set_duty_clamps_and_raises():
    heater = HeaterPWM(pin=13)
    with pytest.raises(ValueError):
        heater.set_duty(2000)
    assert heater.duty == 0
    assert heater.pwm._duty == 0
    with pytest.raises(ValueError):
        heater.set_duty(-1)
    assert heater.duty == 0
    assert heater.pwm._duty == 0

@patch('app.actuators.heater.PWM', DummyPWM)
@patch('app.actuators.heater.Pin', MagicMock)
def test_heater_pwm_off():
    heater = HeaterPWM(pin=13)
    heater.set_duty(400)
    heater.off()
    assert heater.duty == 0
    assert heater.pwm._duty == 0

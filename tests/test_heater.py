import pytest
from unittest.mock import MagicMock, patch

from app.actuators.heater import BoilerHeaterPWM, SuperheaterHeaterPWM, HeaterActuators

class DummyPWM:
    def __init__(self, pin, freq=1000):
        self.pin = pin
        self.freq = freq
        self._duty = 0
    def duty(self, value):
        self._duty = value

@patch('app.actuators.heater.PWM', DummyPWM)
@patch('app.actuators.heater.Pin', MagicMock)
def test_boiler_heater_pwm_init_sets_duty_zero():
    heater = BoilerHeaterPWM()
    assert heater.duty == 0
    assert heater.pwm._duty == 0

@patch('app.actuators.heater.PWM', DummyPWM)
@patch('app.actuators.heater.Pin', MagicMock)
def test_superheater_heater_pwm_init_sets_duty_zero():
    heater = SuperheaterHeaterPWM()
    assert heater.duty == 0
    assert heater.pwm._duty == 0

@patch('app.actuators.heater.PWM', DummyPWM)
@patch('app.actuators.heater.Pin', MagicMock)
def test_boiler_heater_pwm_set_duty_valid():
    heater = BoilerHeaterPWM()
    heater.set_duty(512)
    assert heater.duty == 512
    assert heater.pwm._duty == 512

@patch('app.actuators.heater.PWM', DummyPWM)
@patch('app.actuators.heater.Pin', MagicMock)
def test_superheater_heater_pwm_set_duty_valid():
    heater = SuperheaterHeaterPWM()
    heater.set_duty(256)
    assert heater.duty == 256
    assert heater.pwm._duty == 256

@patch('app.actuators.heater.PWM', DummyPWM)
@patch('app.actuators.heater.Pin', MagicMock)
def test_boiler_heater_pwm_set_duty_clamps_and_raises():
    heater = BoilerHeaterPWM()
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
def test_superheater_heater_pwm_set_duty_clamps_and_raises():
    heater = SuperheaterHeaterPWM()
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
def test_boiler_heater_pwm_off():
    heater = BoilerHeaterPWM()
    heater.set_duty(400)
    heater.off()
    assert heater.duty == 0
    assert heater.pwm._duty == 0

@patch('app.actuators.heater.PWM', DummyPWM)
@patch('app.actuators.heater.Pin', MagicMock)
def test_superheater_heater_pwm_off():
    heater = SuperheaterHeaterPWM()
    heater.set_duty(400)
    heater.off()
    assert heater.duty == 0
    assert heater.pwm._duty == 0

@patch('app.actuators.heater.PWM', DummyPWM)
@patch('app.actuators.heater.Pin', MagicMock)
def test_heater_actuators_composite():
    heaters = HeaterActuators()
    heaters.set_boiler_duty(600)
    heaters.set_superheater_duty(300)
    assert heaters.boiler.duty == 600
    assert heaters.superheater.duty == 300
    heaters.all_off()
    assert heaters.boiler.duty == 0
    assert heaters.superheater.duty == 0


import pytest
from unittest.mock import MagicMock, patch
from app.actuators.boiler_heater import BoilerHeaterPWM
from app.actuators.superheater_heater import SuperheaterHeaterPWM


class DummyPWM:
    def __init__(self, pin, freq=1000):
        self.pin = pin
        self.freq = freq
        self._duty = 0
    def duty(self, value):
        self._duty = value

def test_boiler_heater_pwm_init_sets_duty_zero():
    with patch('app.actuators.boiler_heater.PWM', DummyPWM), patch('app.actuators.boiler_heater.Pin', MagicMock):
        heater = BoilerHeaterPWM()
        assert heater.duty == 0
        assert heater.pwm._duty == 0

def test_superheater_heater_pwm_init_sets_duty_zero():
    with patch('app.actuators.superheater_heater.PWM', DummyPWM), patch('app.actuators.superheater_heater.Pin', MagicMock):
        heater = SuperheaterHeaterPWM()
        assert heater.duty == 0
        assert heater.pwm._duty == 0

def test_boiler_heater_pwm_set_duty_valid():
    with patch('app.actuators.boiler_heater.PWM', DummyPWM), patch('app.actuators.boiler_heater.Pin', MagicMock):
        heater = BoilerHeaterPWM()
        heater.set_duty(512)
        assert heater.duty == 512
        assert heater.pwm._duty == 512

def test_superheater_heater_pwm_set_duty_valid():
    with patch('app.actuators.superheater_heater.PWM', DummyPWM), patch('app.actuators.superheater_heater.Pin', MagicMock):
        heater = SuperheaterHeaterPWM()
        heater.set_duty(256)
        assert heater.duty == 256
        assert heater.pwm._duty == 256

def test_boiler_heater_pwm_set_duty_clamps_and_raises():
    with patch('app.actuators.boiler_heater.PWM', DummyPWM), patch('app.actuators.boiler_heater.Pin', MagicMock):
        heater = BoilerHeaterPWM()
        with pytest.raises(ValueError):
            heater.set_duty(2000)
        assert heater.duty == 0
        assert heater.pwm._duty == 0
        with pytest.raises(ValueError):
            heater.set_duty(-1)
        assert heater.duty == 0
        assert heater.pwm._duty == 0

def test_superheater_heater_pwm_set_duty_clamps_and_raises():
    with patch('app.actuators.superheater_heater.PWM', DummyPWM), patch('app.actuators.superheater_heater.Pin', MagicMock):
        heater = SuperheaterHeaterPWM()
        with pytest.raises(ValueError):
            heater.set_duty(2000)
        assert heater.duty == 0
        assert heater.pwm._duty == 0
        with pytest.raises(ValueError):
            heater.set_duty(-1)
        assert heater.duty == 0
        assert heater.pwm._duty == 0

def test_boiler_heater_pwm_off():
    with patch('app.actuators.boiler_heater.PWM', DummyPWM), patch('app.actuators.boiler_heater.Pin', MagicMock):
        heater = BoilerHeaterPWM()
        heater.set_duty(400)
        heater.off()
        assert heater.duty == 0
        assert heater.pwm._duty == 0

def test_superheater_heater_pwm_off():
    with patch('app.actuators.superheater_heater.PWM', DummyPWM), patch('app.actuators.superheater_heater.Pin', MagicMock):
        heater = SuperheaterHeaterPWM()
        heater.set_duty(400)
        heater.off()
        assert heater.duty == 0
        assert heater.pwm._duty == 0


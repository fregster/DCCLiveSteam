
import pytest
from unittest.mock import MagicMock, patch
from app.actuators.__init__ import Actuators


class DummyMech:
    def __init__(self):
        self.current = 0
        self.target = 0
        self.emergency_mode = False
    def set_goal(self, percent, direction, _):
        self.target = percent
    def update(self, _):
        self.current = self.target


class DummyLED:
    pass


@patch('app.actuators.__init__.BoilerHeaterPWM')
@patch('app.actuators.__init__.SuperheaterHeaterPWM')
def test_actuators_heater_split(mock_superheater, mock_boiler):
    # Setup mocks
    boiler_mock = MagicMock()
    superheater_mock = MagicMock()
    mock_boiler.return_value = boiler_mock
    mock_superheater.return_value = superheater_mock

    mech = DummyMech()
    green_led = DummyLED()
    firebox_led = DummyLED()
    a = Actuators(mech, green_led, firebox_led)
    a.set_boiler_duty(700)
    a.set_superheater_duty(350)
    boiler_mock.set_duty.assert_called_with(700)
    superheater_mock.set_duty.assert_called_with(350)
    a.all_off()
    boiler_mock.off.assert_called()

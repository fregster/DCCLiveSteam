"""
Unit tests for StatusLEDManager (app/status_led.py)
"""
from app.status_led import StatusLEDManager
from unittest.mock import MagicMock

def test_update_motion():
    led = MagicMock()
    manager = StatusLEDManager(led)
    manager.update(True, False)
    led.moving_flash.assert_called_once()
    led.update.assert_called_once()

def test_update_ready():
    led = MagicMock()
    manager = StatusLEDManager(led)
    manager.update(False, True)
    led.solid.assert_called_once()
    led.update.assert_called_once()

def test_update_off():
    led = MagicMock()
    manager = StatusLEDManager(led)
    manager.update(False, False)
    led.off.assert_called_once()
    led.update.assert_called_once()
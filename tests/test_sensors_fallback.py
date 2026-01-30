"""
Unit tests for SensorSuite health check and degraded mode flags.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.sensors import SensorSuite

def test_sensor_suite_speed_sensor_health_flag():
    """
    SensorSuite should set speed_sensor_available=False if speed sensor init fails.
    """
    with patch("app.sensors.SpeedSensor", side_effect=Exception("fail")):
        sensors = SensorSuite()
        assert sensors.speed_sensor_available is False

def test_sensor_suite_pressure_sensor_health_flag():
    """
    SensorSuite should set pressure_sensor_available=False if pressure sensor read fails.
    """
    with patch("app.sensors.read_pressure", side_effect=Exception("fail")):
        sensors = SensorSuite()
        assert sensors.pressure_sensor_available is False

def test_sensor_suite_check_health_runtime():
    """
    SensorSuite.check_health() should update flags if sensors fail at runtime.
    """
    sensors = SensorSuite()
    # Simulate runtime failure
    failing_mock = MagicMock()
    failing_mock.update_encoder.side_effect = Exception("fail")
    sensors.speed_sensor = failing_mock
    sensors.adc_pressure = MagicMock()
    with patch("app.sensors.read_pressure", side_effect=Exception("fail")):
        health = sensors.check_health()
        assert health["speed_sensor"] is False
        assert health["pressure_sensor"] is False

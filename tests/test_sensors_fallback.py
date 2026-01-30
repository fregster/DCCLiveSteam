"""
Unit tests for SensorSuite health check and degraded mode flags.
"""
from unittest.mock import patch, MagicMock
from app.sensors import SensorSuite

def test_sensor_suite_speed_sensor_health_flag():
    """
    SensorSuite should set speed_sensor_available=False if speed sensor init fails.
    """
    from unittest.mock import Mock
    def mock_pin_factory(pin):
        return Mock()
    def mock_adc_factory(pin):
        adc = Mock()
        adc.read = Mock(return_value=2048)
        return adc
    # Patch the correct import path used in SensorSuite
    with patch("app.sensors.speed_sensor.SpeedSensor", side_effect=Exception("fail")):
        sensors = SensorSuite(adc_factory=mock_adc_factory, pin_factory=mock_pin_factory, encoder_hw=Mock())
        assert sensors.speed_sensor_available is False

def test_sensor_suite_pressure_sensor_health_flag():
    """
    SensorSuite should set pressure_sensor_available=False if pressure sensor read fails.
    """
    from unittest.mock import Mock
    def mock_pin_factory(pin):
        return Mock()
    def mock_adc_factory(pin):
        adc = Mock()
        adc.read = Mock(return_value=2048)
        return adc
    with patch("app.sensors.read_pressure", side_effect=Exception("fail")):
        sensors = SensorSuite(adc_factory=mock_adc_factory, pin_factory=mock_pin_factory, encoder_hw=Mock())
        assert sensors.pressure_sensor_available is False

def test_sensor_suite_check_health_runtime():
    """
    SensorSuite.check_health() should update flags if sensors fail at runtime.
    """
    from unittest.mock import Mock, MagicMock
    def mock_pin_factory(pin):
        return Mock()
    def mock_adc_factory(pin):
        adc = Mock()
        adc.read = Mock(return_value=2048)
        return adc
    sensors = SensorSuite(adc_factory=mock_adc_factory, pin_factory=mock_pin_factory, encoder_hw=Mock())
    # Simulate runtime failure
    failing_mock = MagicMock()
    failing_mock.update_encoder.side_effect = Exception("fail")
    sensors.speed_sensor = failing_mock
    sensors.adc_pressure = MagicMock()
    with patch("app.sensors.read_pressure", side_effect=Exception("fail")):
        health = sensors.check_health()
        assert health["speed_sensor"] is False
        assert health["pressure_sensor"] is False

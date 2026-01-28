"""
Unit tests for sensors.py module.
Tests ADC reading, temperature conversion, and encoder tracking.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from app.sensors import SensorSuite


@pytest.fixture
def mock_hardware(monkeypatch):
    """Mocks all hardware dependencies for SensorSuite."""
    # Mock is already done in conftest.py
    return None


def test_sensor_suite_initialization(mock_hardware):
    """
    Tests SensorSuite initializes all ADCs and encoder pin.
    
    Why: Ensures hardware is properly configured on boot.
    
    Safety: Missing sensor initialization could cause reads to fail.
    """
    sensors = SensorSuite()
    
    assert sensors.adc_boiler is not None
    assert sensors.adc_super is not None
    assert sensors.adc_track is not None
    assert sensors.adc_pressure is not None
    assert sensors.adc_logic is not None
    assert sensors.encoder_pin is not None
    assert sensors.encoder_count == 0


def test_read_adc_oversampling(mock_hardware):
    """
    Tests that _read_adc performs oversampling correctly.
    
    Why: Oversampling reduces ADC noise for stable readings.
    """
    sensors = SensorSuite()
    
    # Mock ADC to return consistent value
    mock_adc = Mock()
    mock_adc.read = Mock(return_value=2048)
    
    result = sensors._read_adc(mock_adc)
    
    assert result == 2048
    assert mock_adc.read.call_count == 10  # ADC_SAMPLES = 10


def test_adc_to_temp_zero_input(mock_hardware):
    """
    Tests temperature conversion with zero ADC value.
    
    Why: Zero ADC indicates disconnected sensor.
    
    Safety: Should return 999.9°C to trigger thermal shutdown watchdog.
    """
    sensors = SensorSuite()
    temp = sensors._adc_to_temp(0)
    
    assert temp == 999.9  # Trigger thermal shutdown


def test_adc_to_temp_normal_range(mock_hardware):
    """
    Tests temperature conversion with typical ADC values.
    
    Why: Validates Steinhart-Hart equation implementation.
    """
    sensors = SensorSuite()
    
    # Mid-range ADC value should give reasonable temperature
    temp = sensors._adc_to_temp(2048)
    
    assert -50 < temp < 150  # Reasonable temperature range


def test_adc_to_temp_boundary_values(mock_hardware):
    """
    Tests temperature conversion at ADC boundaries.
    
    Why: Edge cases often expose calculation errors.
    
    Safety: Invalid ADC values must not crash or return absurd temperatures.
    """
    sensors = SensorSuite()
    
    # Maximum ADC value - treated as sensor failure (voltage = 3.3V, infinite resistance)
    temp_max = sensors._adc_to_temp(4095)
    assert temp_max == 999.9  # Fail-safe value triggers shutdown
    
    # Near-zero ADC - very low resistance, physically corresponds to very high temp
    temp_min = sensors._adc_to_temp(1)
    assert temp_min > 200  # Low ADC = low resistance = high temp (Steinhart-Hart)


def test_read_temps_returns_tuple(mock_hardware):
    """
    Tests that read_temps returns three temperature values.
    
    Why: Main loop expects (boiler, super, logic) tuple.
    """
    sensors = SensorSuite()
    
    temps = sensors.read_temps()
    
    assert isinstance(temps, tuple)
    assert len(temps) == 3
    assert all(isinstance(t, float) for t in temps)


def test_read_track_voltage_scaling(mock_hardware):
    """
    Tests track voltage scaling with voltage divider.
    
    Why: 5x voltage divider allows measuring up to 16.5V DCC signals.
    """
    sensors = SensorSuite()
    
    # Mock ADC to return half-scale
    sensors.adc_track._value = 2048
    
    voltage = sensors.read_track_voltage()
    
    assert isinstance(voltage, int)
    assert 0 < voltage < 20000  # Should be in millivolts


def test_read_pressure_range(mock_hardware):
    """
    Tests pressure sensor reading range (0-100 PSI).
    
    Why: Validates pressure transducer scaling.
    
    Safety: Out-of-range pressure readings could indicate sensor failure.
    """
    sensors = SensorSuite()
    
    # Mock ADC for zero pressure
    sensors.adc_pressure._value = 0
    pressure_zero = sensors.read_pressure()
    assert pressure_zero == 0.0
    
    # Mock ADC for full scale
    sensors.adc_pressure._value = 4095
    pressure_max = sensors.read_pressure()
    assert 99.0 < pressure_max <= 100.0


def test_update_encoder_increments_on_falling_edge(mock_hardware):
    """
    Tests encoder count increments on falling edges.
    
    Why: Optical encoder triggers on falling edge of slot transitions.
    """
    sensors = SensorSuite()
    initial_count = sensors.encoder_count
    
    # Simulate encoder pin going high then low
    sensors.encoder_pin._value = 1
    sensors.encoder_last = 1
    sensors.update_encoder()
    
    assert sensors.encoder_count == initial_count  # No change yet
    
    sensors.encoder_pin._value = 0
    sensors.update_encoder()
    
    assert sensors.encoder_count == initial_count + 1


def test_update_encoder_no_increment_on_rising_edge(mock_hardware):
    """
    Tests encoder does NOT increment on rising edges.
    
    Why: Only falling edges are counted to avoid double-counting.
    """
    sensors = SensorSuite()
    sensors.encoder_last = 0
    sensors.encoder_pin._value = 0
    initial_count = sensors.encoder_count
    
    # Rising edge
    sensors.encoder_pin._value = 1
    sensors.update_encoder()
    
    assert sensors.encoder_count == initial_count  # No increment


def test_encoder_overflow_handling(mock_hardware):
    """
    Tests encoder counter can handle large values.
    
    Why: Counter should not overflow during extended operation.
    """
    sensors = SensorSuite()
    sensors.encoder_count = 999999
    
    sensors.encoder_pin._value = 0
    sensors.encoder_last = 1
    sensors.update_encoder()
    
    assert sensors.encoder_count == 1000000


def test_sensor_disconnection_detection(mock_hardware):
    """
    Tests that sensor failures return safe values.
    
    Why: Disconnected sensors should not cause crashes or invalid readings.
    
    Safety: CRITICAL - sensor failures must be detectable.
    """
    sensors = SensorSuite()
    
    # Simulate disconnected thermistor (zero ADC)
    sensors.adc_boiler._value = 0
    temps = sensors.read_temps()
    
    assert temps[0] == 999.9  # Fail-safe triggers thermal shutdown


def test_all_temps_independent(mock_hardware):
    """
    Tests that temperature sensors read independently.
    
    Why: Each sensor must be isolated - failure of one should not affect others.
    """
    sensors = SensorSuite()
    
    # Set different ADC values
    sensors.adc_boiler._value = 1000
    sensors.adc_super._value = 2000
    sensors.adc_logic._value = 3000
    
    temps = sensors.read_temps()
    
    # All should be different
    assert temps[0] != temps[1]
    assert temps[1] != temps[2]
    assert temps[0] != temps[2]


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-W', 'error'])

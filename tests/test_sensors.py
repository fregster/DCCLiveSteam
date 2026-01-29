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
    
    # First get a valid reading and cache it
    sensors.adc_boiler.read = Mock(side_effect=[2048] * 10)
    sensors.adc_super.read = Mock(side_effect=[2048] * 10)
    sensors.adc_logic.read = Mock(side_effect=[2048] * 10)
    temps = sensors.read_temps()
    cached_boiler = temps[0]
    
    # Now simulate disconnected thermistor (zero ADC = 999.9, which is invalid)
    sensors.adc_boiler.read = Mock(side_effect=[0] * 30)
    sensors.adc_super.read = Mock(side_effect=[2048] * 30)
    sensors.adc_logic.read = Mock(side_effect=[2048] * 30)
    temps = sensors.read_temps()
    
    # In new graceful degradation mode: returns cached value instead of 999.9
    assert temps[0] == cached_boiler
    # But marks sensor as DEGRADED
    health = sensors.get_health_status()
    assert health["boiler_temp"] == "DEGRADED"


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


# NEW: Sensor health tracking tests

def test_sensor_health_initialization(mock_hardware):
    """
    Tests that sensor health is initialized to NOMINAL.
    
    Why: System starts with all sensors assumed healthy.
    """
    sensors = SensorSuite()
    
    health = sensors.get_health_status()
    assert health["boiler_temp"] == "NOMINAL"
    assert health["super_temp"] == "NOMINAL"
    assert health["logic_temp"] == "NOMINAL"
    assert health["pressure"] == "NOMINAL"
    assert sensors.failed_sensor_count == 0


def test_is_reading_valid_boiler_temp(mock_hardware):
    """
    Tests boiler temperature validity check.
    
    Why: Detects sensor failures (disconnected = 999.9°C, open = 0°C, etc.)
    
    Safety: Conservative range 0-150°C catches anomalies immediately.
    """
    sensors = SensorSuite()
    
    # Valid readings
    assert sensors.is_reading_valid(25.0, "boiler_temp") is True
    assert sensors.is_reading_valid(0.0, "boiler_temp") is True
    assert sensors.is_reading_valid(150.0, "boiler_temp") is True
    
    # Invalid readings
    assert sensors.is_reading_valid(999.9, "boiler_temp") is False
    assert sensors.is_reading_valid(-10.0, "boiler_temp") is False
    assert sensors.is_reading_valid(160.0, "boiler_temp") is False


def test_is_reading_valid_super_temp(mock_hardware):
    """Tests superheater temperature validity check."""
    sensors = SensorSuite()
    
    # Valid readings
    assert sensors.is_reading_valid(200.0, "super_temp") is True
    assert sensors.is_reading_valid(280.0, "super_temp") is True
    
    # Invalid readings
    assert sensors.is_reading_valid(300.0, "super_temp") is False
    assert sensors.is_reading_valid(-5.0, "super_temp") is False


def test_is_reading_valid_logic_temp(mock_hardware):
    """Tests TinyPICO die temperature validity check."""
    sensors = SensorSuite()
    
    # Valid readings
    assert sensors.is_reading_valid(45.0, "logic_temp") is True
    assert sensors.is_reading_valid(100.0, "logic_temp") is True
    
    # Invalid readings
    assert sensors.is_reading_valid(120.0, "logic_temp") is False
    assert sensors.is_reading_valid(-1.0, "logic_temp") is False


def test_is_reading_valid_pressure(mock_hardware):
    """Tests pressure sensor validity check."""
    sensors = SensorSuite()
    
    # Valid readings
    assert sensors.is_reading_valid(18.0, "pressure") is True
    assert sensors.is_reading_valid(0.0, "pressure") is True
    assert sensors.is_reading_valid(30.0, "pressure") is True
    assert sensors.is_reading_valid(-1.0, "pressure") is True
    
    # Invalid readings
    assert sensors.is_reading_valid(35.0, "pressure") is False
    assert sensors.is_reading_valid(-2.0, "pressure") is False


def test_read_temps_with_valid_sensors(mock_hardware):
    """
    Tests read_temps with all sensors healthy.
    
    Why: Normal operation should maintain NOMINAL health status.
    """
    sensors = SensorSuite()
    
    # Mock ADC readings to return valid values
    sensors.adc_boiler.read = Mock(side_effect=[2048] * 10)  # ~25°C
    sensors.adc_super.read = Mock(side_effect=[2048] * 10)
    sensors.adc_logic.read = Mock(side_effect=[2048] * 10)
    
    temps = sensors.read_temps()
    
    # All temps should be valid
    assert 0 < temps[0] < 150  # boiler
    assert 0 < temps[1] < 280  # super
    assert 0 < temps[2] < 100  # logic
    
    # All sensors should still be NOMINAL
    health = sensors.get_health_status()
    assert health["boiler_temp"] == "NOMINAL"
    assert health["super_temp"] == "NOMINAL"
    assert health["logic_temp"] == "NOMINAL"
    assert sensors.failed_sensor_count == 0


def test_read_temps_with_failed_boiler_sensor(mock_hardware):
    """
    Tests graceful degradation when boiler sensor fails.
    
    Why: Failed sensor (999.9°C) should be marked DEGRADED, use cached value.
    
    Safety: Doesn't return invalid value, uses last-valid cached reading.
    """
    sensors = SensorSuite()
    
    # First good read
    sensors.adc_boiler.read = Mock(side_effect=[2048] * 10)
    sensors.adc_super.read = Mock(side_effect=[2048] * 10)
    sensors.adc_logic.read = Mock(side_effect=[2048] * 10)
    temps1 = sensors.read_temps()
    cached_boiler = temps1[0]
    
    # Now boiler returns 0 (open circuit = 999.9°C)
    sensors.adc_boiler.read = Mock(side_effect=[0] * 10)
    sensors.adc_super.read = Mock(side_effect=[2048] * 10)
    sensors.adc_logic.read = Mock(side_effect=[2048] * 10)
    temps2 = sensors.read_temps()
    
    # Boiler should return cached value, not 999.9
    assert temps2[0] == cached_boiler
    
    # Boiler should be marked DEGRADED
    health = sensors.get_health_status()
    assert health["boiler_temp"] == "DEGRADED"
    assert health["super_temp"] == "NOMINAL"
    assert sensors.failed_sensor_count == 1
    assert "boiler_temp" in sensors.failure_reason


def test_read_temps_with_multiple_failed_sensors(mock_hardware):
    """
    Tests detection of multiple sensor failures (critical condition).
    
    Why: Multiple failures should be detected and reported as CRITICAL.
    """
    sensors = SensorSuite()
    
    # Both boiler and logic sensors fail
    sensors.adc_boiler.read = Mock(side_effect=[0] * 10)  # Open
    sensors.adc_super.read = Mock(side_effect=[2048] * 10)  # OK
    sensors.adc_logic.read = Mock(side_effect=[4095] * 10)  # Open
    
    temps = sensors.read_temps()
    
    # Both should be marked DEGRADED
    health = sensors.get_health_status()
    assert health["boiler_temp"] == "DEGRADED"
    assert health["logic_temp"] == "DEGRADED"
    assert health["super_temp"] == "NOMINAL"
    assert sensors.failed_sensor_count == 2
    assert "boiler_temp" in sensors.failure_reason
    assert "logic_temp" in sensors.failure_reason


def test_sensor_recovery_from_degraded(mock_hardware):
    """
    Tests that sensor marked DEGRADED recovers when reading becomes valid.
    
    Why: Glitch (momentary disconnection) shouldn't permanently mark as failed.
    """
    sensors = SensorSuite()
    
    # Start with good reading
    sensors.adc_boiler.read = Mock(side_effect=[2048] * 10)
    sensors.adc_super.read = Mock(side_effect=[2048] * 10)
    sensors.adc_logic.read = Mock(side_effect=[2048] * 10)
    sensors.read_temps()
    
    # Sensor fails - need fresh mocks with enough values
    sensors.adc_boiler.read = Mock(side_effect=[0] * 30)  # 30 values for 3 calls
    sensors.adc_super.read = Mock(side_effect=[2048] * 30)
    sensors.adc_logic.read = Mock(side_effect=[2048] * 30)
    sensors.read_temps()
    health = sensors.get_health_status()
    assert health["boiler_temp"] == "DEGRADED"
    
    # Sensor recovers
    sensors.adc_boiler.read = Mock(side_effect=[2048] * 10)
    sensors.adc_super.read = Mock(side_effect=[2048] * 10)
    sensors.adc_logic.read = Mock(side_effect=[2048] * 10)
    sensors.read_temps()
    health = sensors.get_health_status()
    assert health["boiler_temp"] == "NOMINAL"
    assert sensors.failed_sensor_count == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-W', 'error'])


"""
Unit tests for PressureManager fallback and degraded mode.
"""
from app.managers.pressure_manager import PressureManager
from unittest.mock import MagicMock
def test_pressure_manager_fallback_to_temp_only():
    """
    If pressure sensor is unavailable or fails, PressureManager should use temp-only fallback logic.
    """
    cv = {33: 40.0, 35: 60.0, 43: 250}
    actuators = MagicMock()
    pm = PressureManager(actuators, cv)
    pm.pressure_sensor_available = False
    # Superheater temp below limit-10: boiler ON at 30%
    pm.process(0, 0, 200.0, 0.1)
    actuators.set_boiler_duty.assert_called_with(int(0.3 * 1023))
    # Superheater temp above limit-10: boiler OFF
    pm.process(0, 0, 241.0, 0.1)
    actuators.set_boiler_duty.assert_called_with(0)
    # Superheater temp above limit: superheater OFF
    pm.process(0, 0, 251.0, 0.1)
    actuators.set_superheater_duty.assert_called_with(0)
    # Superheater temp below limit: superheater ON at 25%
    pm.process(0, 0, 200.0, 0.1)
    actuators.set_superheater_duty.assert_called_with(int(0.25 * 1023))

def test_pressure_manager_runtime_sensor_failure():
    """
    If pressure sensor fails at runtime, PressureManager should switch to temp-only fallback logic.
    """
    cv = {33: 40.0, 35: 60.0, 43: 250}
    actuators = MagicMock()
    pm = PressureManager(actuators, cv)
    pm.pressure_sensor_available = True
    pm.process(0, 0, 200.0, 0.1)  # Should run normal
    pm.pressure_sensor_available = False
    pm.process(0, 0, 200.0, 0.1)
    actuators.set_boiler_duty.assert_called_with(int(0.3 * 1023))

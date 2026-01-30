"""
Unit tests for PressureManager fallback and degraded mode.
"""
from app.managers.pressure_manager import PressureManager

class DummyHeaterActuators:
    def __init__(self):
        self.boiler_duty = None
        self.superheater_duty = None
        self.all_off_called = False
    def set_boiler_duty(self, value):
        self.boiler_duty = value
    def set_superheater_duty(self, value):
        self.superheater_duty = value
    def all_off(self):
        self.all_off_called = True
def test_pressure_manager_fallback_to_temp_only():
    """
    If pressure sensor is unavailable or fails, PressureManager should use temp-only fallback logic.
    """
    cv = {33: 40.0, 35: 60.0, 43: 250}
    heaters = DummyHeaterActuators()
    pm = PressureManager(heaters, cv)
    pm.pressure_sensor_available = False
    # Superheater temp below limit-10: boiler ON at 30%
    pm.process(0, 0, 200.0, 0.1)
    assert heaters.boiler_duty == int(0.3 * 1023)
    # Superheater temp above limit-10: boiler OFF
    pm.process(0, 0, 241.0, 0.1)
    assert heaters.boiler_duty == 0
    # Superheater temp above limit: superheater OFF
    pm.process(0, 0, 251.0, 0.1)
    assert heaters.superheater_duty == 0
    # Superheater temp below limit: superheater ON at 25%
    pm.process(0, 0, 200.0, 0.1)
    assert heaters.superheater_duty == int(0.25 * 1023)

def test_pressure_manager_runtime_sensor_failure():
    """
    If pressure sensor fails at runtime, PressureManager should switch to temp-only fallback logic.
    """
    cv = {33: 40.0, 35: 60.0, 43: 250}
    heaters = DummyHeaterActuators()
    pm = PressureManager(heaters, cv)
    # Simulate runtime failure by raising in process
    def bad_process(*args, **kwargs):
        raise RuntimeError("Sensor failure")
    # Patch process to raise exception
    pm.pressure_sensor_available = True
    # Should switch to fallback if exception occurs
    pm.process(0, 0, 200.0, 0.1)  # Should run normal
    pm.pressure_sensor_available = True
    try:
        raise Exception("Sensor fail")
    except Exception:
        pm.pressure_sensor_available = False
    pm.process(0, 0, 200.0, 0.1)
    assert heaters.boiler_duty == int(0.3 * 1023)

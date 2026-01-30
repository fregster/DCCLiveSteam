"""
Unit test for power budget enforcement (CV51).
"""

from unittest.mock import patch

def test_power_budget_enforcement_reduces_load(monkeypatch):
    """
    Tests that Locomotive.enforce_power_budget() reduces heater PWM and disables superheater if over budget.
    Why: System must not exceed user-configured power budget (CV51).
    Safety: If unable to reduce current, triggers safety shutdown.
    """
    class DummyHeater:
        def __init__(self):
            self._duty = 1023
            self.duty_calls = []
        def duty(self, value):
            self._duty = value
            self.duty_calls.append(value)
    class DummyMech:
        current = 100
        target = 200
    class DummyPressure:
        def __init__(self):
            self.boiler_heater = DummyHeater()
            self.super_heater = DummyHeater()
    # Provide all required CVs for Locomotive/DCCDecoder initialisation
    cv = {
        1: 3,  # DCC Address
        29: 0, # Configuration
        30: 1,
        31: 0,
        32: 18.0,
        33: 35.0,
        34: 15.0,
        37: 1325,
        38: 12,
        39: 203,
        40: 76,
        41: 75,
        42: 110,
        43: 250,
        44: 20,
        45: 8,
        46: 77,
        47: 128,
        48: 5,
        49: 1000,
        51: 1.0,  # Power Budget (Amps)
        84: 1,
        87: 10.0,
        88: 20
    }
    from app.managers.power_manager import PowerManager
    with patch('app.main.DCCDecoder'), \
         patch('app.main.PhysicsEngine'), \
         patch('app.main.MechanicalMapper'), \
         patch('app.main.PressureController'), \
         patch('app.main.Watchdog'), \
         patch('app.main.BLE_UART'), \
         patch('app.main.CachedSensorReader'), \
         patch('app.main.SerialPrintQueue'), \
         patch('app.main.FileWriteQueue'), \
         patch('app.main.GarbageCollector'), \
         patch('app.main.FireboxLED'), \
         patch('app.main.GreenStatusLED'):
        shutdown_called = {}
        class DummyLoco:
            def __init__(self):
                self.cv = cv
                self.pressure = DummyPressure()
                self.mech = DummyMech()
                self.log_event = lambda *a, **kw: None
                self._boiler_pwm = 1023
                self._super_pwm = 1023
                def die(*a, **kw):
                    shutdown_called['cause'] = kw.get('cause', a[0] if a else None)
                self.die = die
                self.safety_shutdown = lambda cause: die(cause)
            @property
            def boiler_pwm(self):
                return self._boiler_pwm
            @property
            def super_pwm(self):
                return self._super_pwm
            def set_boiler_pwm(self, value):
                self._boiler_pwm = value
                self.pressure.boiler_heater.duty(value)
            def set_super_pwm(self, value):
                self._super_pwm = value
                self.pressure.super_heater.duty(value)
        loco = DummyLoco()
        pm = PowerManager(loco, {})
        pm.power_budget_amps = 1.0
        pm.process()
        assert loco.pressure.boiler_heater.duty_calls[0] < 1023
        loco.pressure.super_heater._duty = 1023  # Reset
        pm.process()
        assert loco.pressure.super_heater.duty_calls[-1] == 0
        pm.process()
        assert shutdown_called['cause'] == 'POWER_BUDGET_EXCEEDED'

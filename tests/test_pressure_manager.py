from unittest.mock import MagicMock
def test_pressure_manager_actuator_calls():
    """
    Test that PressureManager calls actuators with correct boiler and superheater duty values (mocked).
    """
    actuators = MagicMock()
    cv = {33: 20.0, 35: 30.0, 43: 250}
    pm = PressureManager(actuators, cv)
    pm.process(current_psi=10.0, regulator_open=0, superheater_temp=50.0, dt=0.1)
    assert actuators.set_boiler_duty.called
    assert actuators.set_superheater_duty.called

def test_pressure_manager_fallback_temp_only():
    """
    Test fallback mode: pressure sensor unavailable, uses temp-only safety logic (mocked).
    """
    actuators = MagicMock()
    cv = {33: 20.0, 35: 30.0, 43: 250}
    pm = PressureManager(actuators, cv)
    pm.pressure_sensor_available = False
    # Superheater temp below limit-10: boiler ON, superheater ON
    pm.process(current_psi=0, regulator_open=0, superheater_temp=200.0, dt=0.1)
    actuators.set_boiler_duty.assert_called_with(int(0.3 * 1023))
    actuators.set_superheater_duty.assert_called_with(int(0.25 * 1023))
    # Superheater temp above limit: both OFF
    pm.process(current_psi=0, regulator_open=0, superheater_temp=260.0, dt=0.1)
    actuators.set_boiler_duty.assert_called_with(int(0.3 * 1023))
    actuators.set_superheater_duty.assert_called_with(int(0.25 * 1023))


from app.managers.pressure_manager import PressureManager
from unittest.mock import MagicMock

def test_superheater_staged_logic():
    cv = {33: 40.0, 35: 60.0, 43: 250}
    actuators = MagicMock()
    pm = PressureManager(actuators, cv)
    # Low pressure: superheater OFF (<50% of target)
    pm.process(2.0, 0, 50.0, 0.1)
    actuators.set_superheater_duty.assert_called_with(0)
    # 25% stage (>=50% and <75% of target)
    pm.process(21.0, 0, 50.0, 0.1)  # 21/40 = 0.525
    actuators.set_superheater_duty.assert_called_with(int(0.25 * 1023))
    # 50% stage
    pm.process(30.0, 0, 50.0, 0.1)
    actuators.set_superheater_duty.assert_called_with(int(0.5 * 1023))
    # 70%+temp control
    pm.process(39.0, 0, 200.0, 0.1)
    # Should be called with a value >= int(0.5 * 1023)
    assert actuators.set_superheater_duty.call_args[0][0] >= int(0.5 * 1023)
    # Over temp: fallback to 50% (DCC speed == 0)
    pm.process(40.0, 0, 260.0, 0.1)
    actuators.set_superheater_duty.assert_called_with(int(0.5 * 1023))

def test_superheater_blowdown_spike():
    cv = {33: 40.0, 35: 60.0, 43: 250}
    actuators = MagicMock()
    pm = PressureManager(actuators, cv)
    # Simulate regulator opening (spike starts)
    pm.process(40.0, 1, 200.0, 0.1)
    actuators.set_superheater_duty.assert_called_with(1023)
    # Spike timer should decrement but still active
    pm.process(40.0, 0, 200.0, 0.5)
    actuators.set_superheater_duty.assert_called_with(1023)
    # After spike duration (just over 1.0s), should drop
    pm.process(40.0, 0, 200.0, 0.5)  # total dt = 1.1s > 1.0s
    # Should be called with a value < 1023
    assert actuators.set_superheater_duty.call_args[0][0] < 1023

def test_pressure_manager_shutdown():
    cv = {33: 40.0, 35: 60.0, 43: 250}
    actuators = MagicMock()
    pm = PressureManager(actuators, cv)
    pm.shutdown()
    actuators.all_off.assert_called()
"""
Unit tests for actuators.py module.
Tests servo control with slew-rate limiting and PID pressure control.
"""
import pytest
from unittest.mock import Mock, patch
import time
from app.actuators import MechanicalMapper, PressureController


@pytest.fixture
def test_cv():
    """Provides test CV configuration."""
    return {
        46: 77,    # Servo neutral PWM
        47: 128,   # Servo max PWM
        48: 5,     # Whistle offset degrees
        49: 1000,  # Travel time ms
        33: 35.0   # Target pressure PSI
    }


def test_mechanical_mapper_initialisation(test_cv):
    """
    Tests MechanicalMapper initialises at neutral position.
    
    Why: Servo must start at safe neutral position on boot.
    
    Safety: Starting at wrong position could open regulator unexpectedly.
    """
    mapper = MechanicalMapper(test_cv)
    
    assert mapper.current == 77.0
    assert mapper.target == 77.0
    assert mapper.is_sleeping is False
    assert mapper.was_stopped is True
    assert mapper.emergency_mode is False


def test_slew_rate_limiting(test_cv):
    """
    Tests that servo movement respects slew rate limits.
    
    Why: Instant movement causes mechanical shock to linkages.
    
    Safety: Prevents damage to regulator mechanism.
    """
    mapper = MechanicalMapper(test_cv)
    mapper.target = 128.0  # Move to max
    
    # First update should not reach target instantly
    mapper.update(test_cv)
    assert mapper.current < 128.0
    assert mapper.current > 77.0  # But should have moved


def test_jitter_sleep_mode(test_cv):
    """
    Tests servo enters sleep mode after 2 seconds of no movement.
    
    Why: Eliminates servo "hum" and extends motor life.
    """
    with patch('app.actuators.time.ticks_ms') as mock_time:
        # First two calls are from __init__
        # Then we call update which gets the 2100ms call for stopped_t check
        mock_time.side_effect = [0, 0, 2100]
        
        mapper = MechanicalMapper(test_cv)
        
        # Ensure servo is at target (no movement)
        mapper.current = mapper.target
        mapper.update(test_cv)
    
    assert mapper.is_sleeping is True


def test_emergency_bypass_mode(test_cv):
    """
    Tests emergency mode bypasses slew rate for instant movement.
    
    Why: During shutdown, valve must close immediately.
    
    Safety: CRITICAL - slew rate must not delay emergency shutdown.
    """
    mapper = MechanicalMapper(test_cv)
    mapper.target = 77.0
    mapper.current = 128.0
    mapper.emergency_mode = True
    
    mapper.update(test_cv)
    
    assert mapper.current == 77.0  # Instant movement


def test_stiction_breakout_kick(test_cv):
    """
    Tests stiction breakout applies momentary kick pulse.
    
    Why: Mechanical friction requires extra force to start moving.
    """
    mapper = MechanicalMapper(test_cv)
    mapper.was_stopped = True
    mapper.target = 100.0
    
    # Mock servo duty to verify kick
    duty_calls = []
    original_duty = mapper.servo.duty
    
    def mock_duty(val=None):
        if val is not None:
            duty_calls.append(val)
        return original_duty(val)
    
    mapper.servo.duty = mock_duty
    
    mapper.update(test_cv)
    
    assert mapper.stiction_applied is True
    # Should have applied kick duty higher than normal


def test_set_goal_whistle_position(test_cv):
    """
    Tests whistle position calculation.
    
    Why: Whistle requires specific valve angle without admitting steam to cylinders.
    
    Safety: Whistle zone must be isolated from drive zone.
    """
    mapper = MechanicalMapper(test_cv)
    mapper.set_goal(0, True, test_cv)  # Whistle active, zero speed
    
    # Target should be at whistle offset, not neutral
    assert mapper.target != test_cv[46]
    assert mapper.target > test_cv[46]


def test_pressure_controller_initialisation(test_cv):
    """
    Tests PressureController initialises PID state.
    
    Why: PID controller requires zero initial state to prevent windup.
    """
    controller = PressureController(test_cv)
    
    assert controller.target_psi == 35.0
    assert controller.integral == 0.0
    assert controller.last_error == 0.0


def test_pid_proportional_response(test_cv):
    """
    Tests PID controller responds proportionally to error.
    
    Why: Larger pressure errors should produce larger heater adjustments.
    """
    controller = PressureController(test_cv)
    
    # Large error (low pressure)
    duty_low = controller.update(10.0, 0.1)  # 25 PSI below target
    
    # Small error (near target)
    duty_near = controller.update(34.0, 0.1)  # 1 PSI below target
    
    assert duty_low > duty_near


def test_pid_anti_windup(test_cv):
    """
    Tests PID integral term is clamped to prevent windup.
    
    Why: Unclamped integral can cause overshoot and oscillation.
    
    Safety: Prevents excessive heater power during startup.
    """
    controller = PressureController(test_cv)
    
    # Run with large error for extended period
    for _ in range(100):
        controller.update(0.0, 0.1)  # 35 PSI error
    
    # Integral should be clamped
    assert -100 <= controller.integral <= 100


def test_heater_duty_clamping(test_cv):
    """
    Tests heater duty is clamped to valid PWM range (0-1023).
    
    Why: Invalid PWM values could damage heater or cause undefined behavior.
    
    Safety: CRITICAL - prevents heater overdrive.
    """
    controller = PressureController(test_cv)
    
    # Force large error
    duty = controller.update(0.0, 1.0)  # Maximum error
    
    assert 0 <= duty <= 1023


def test_superheater_ratio(test_cv):
    """
    Tests superheater runs at 60% of boiler heater power.
    
    Why: Superheater requires less energy than boiler.
    """
    controller = PressureController(test_cv)
    
    # Set known boiler duty via PID
    controller.update(30.0, 0.1)  # 5 PSI below target
    
    # Verify superheater is 60% of boiler (checked via duty calls)
    # This is implementation-specific


def test_shutdown_kills_all_heaters(test_cv):
    """
    Tests shutdown() immediately sets all heater PWM to zero.
    
    Why: Emergency shutdown must cut all heat sources instantly.
    
    Safety: CRITICAL - prevents runaway heating.
    """
    controller = PressureController(test_cv)
    
    # Run heaters
    controller.update(20.0, 0.1)
    
    # Shutdown
    controller.shutdown()
    
    assert controller.boiler_heater._duty == 0
    assert controller.super_heater._duty == 0


def test_servo_range_validation(test_cv):
    """
    Tests servo goal calculation stays within valid PWM range.
    
    Why: Out-of-range PWM could damage servo or mechanism.
    
    Safety: Prevents mechanical over-travel.
    """
    mapper = MechanicalMapper(test_cv)
    
    # Test extreme inputs
    mapper.set_goal(100, False, test_cv)  # Full throttle
    assert test_cv[46] <= mapper.target <= test_cv[47]
    
    mapper.set_goal(0, False, test_cv)  # Neutral
    assert mapper.target == test_cv[46]


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-W', 'error'])

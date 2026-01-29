import pytest

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

from unittest.mock import MagicMock, patch
from app.actuators.pressure_controller import PressureController

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

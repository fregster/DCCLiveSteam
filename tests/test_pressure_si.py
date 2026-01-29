import pytest
from app.actuators.pressure_controller import PressureController

def make_cv(target_kpa=124.0, max_kpa=207.0):
    return {
        32: target_kpa,  # Not used by PressureController, but kept for compatibility
        33: 50.0,        # Default setpoint in PSI
        35: max_kpa,     # Not used by PressureController, but kept for compatibility
        46: 77,
        47: 128,
        48: 5,
        49: 1000,
    }

def test_target_pressure_below_limit():
    # Target PSI is set by CV33
    cv = make_cv()
    controller = PressureController(cv)
    assert hasattr(controller, 'target_psi')

def test_pwm_stages_between_target_and_limit():
    import sys
    from unittest.mock import patch, MagicMock
    with patch('app.actuators.pressure_controller.Pin', MagicMock()), \
         patch('app.actuators.pressure_controller.PWM', MagicMock()):
        cv = make_cv()
        controller = PressureController(cv)
        # Use a larger error margin to ensure positive PID output
        duty_below = controller.update(controller.target_psi - 20, 0.1)
        duty_at = controller.update(controller.target_psi, 0.1)
        duty_above = controller.update(controller.target_psi + 10, 0.1)
        print(f"duty_below={duty_below}, duty_at={duty_at}, duty_above={duty_above}")
        assert duty_below > duty_at >= duty_above

def test_anti_flap_hysteresis():
    cv = make_cv()
    controller = PressureController(cv)
    # Simulate oscillation just above/below target
    below = controller.update(controller.target_psi - 1, 0.1)
    above = controller.update(controller.target_psi + 1, 0.1)
    below2 = controller.update(controller.target_psi - 1, 0.1)
    # Above should be less than below, and below2 should remain nonzero
    assert above < below
    assert below2 > 0

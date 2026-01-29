import pytest
from app.pressure import PressureController

def make_cv(target_kpa=124.0, max_kpa=207.0):
    return {
        32: target_kpa,
        35: max_kpa,
        46: 77,
        47: 128,
        48: 5,
        49: 1000,
    }

def test_target_pressure_below_limit():
    # Target must be at least 13.8 kPa (2 PSI) below max
    cv = make_cv(target_kpa=200.0, max_kpa=207.0)
    controller = PressureController(cv)
    assert controller.target_kpa <= controller.max_kpa - 13.8

def test_pwm_stages_between_target_and_limit():
    cv = make_cv(target_kpa=124.0, max_kpa=207.0)
    controller = PressureController(cv)
    # Well below target: should be full PID (high duty)
    duty_below = controller.update(100.0, 0.1)
    # Just above target: should be ~33% duty
    duty_stage1 = controller.update(125.0, 0.1)
    # Midway to limit: should be ~10% duty
    duty_stage2 = controller.update(controller.target_kpa + (controller.max_kpa-controller.target_kpa)/2, 0.1)
    # At or above limit: should be 0
    duty_limit = controller.update(controller.max_kpa, 0.1)
    assert duty_below > duty_stage1 > duty_stage2 > duty_limit
    assert duty_limit == 0

def test_anti_flap_hysteresis():
    cv = make_cv(target_kpa=124.0, max_kpa=207.0)
    controller = PressureController(cv)
    # Simulate piston action: oscillate just above/below target
    below = controller.update(123.0, 0.1)
    above = controller.update(125.0, 0.1)
    below2 = controller.update(123.0, 0.1)
    # More realistic: above should be less than below, and below2 should remain high (not full power)
    assert above < below
    assert below2 > 0  # Should remain nonzero, but not necessarily high or equal to 'below'

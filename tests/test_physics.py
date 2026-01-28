"""
Unit tests for physics.py module.
Tests scale velocity conversion and odometry calculations.
"""
import pytest
from app.physics import PhysicsEngine


def test_physics_engine_initialisation():
    """
    Tests PhysicsEngine initialises with correct scale conversion.
    
    Why: Ensures prototype-to-scale velocity is calculated correctly.
    
    Safety: Incorrect scaling could cause regulator overshoot.
    """
    cv = {
        39: 203,  # Prototype speed (km/h)
        40: 76,   # Scale ratio (1:76 OO gauge)
        37: 1325, # Wheel radius (mm * 100)
        38: 12    # Encoder segments
    }
    
    engine = PhysicsEngine(cv)
    
    # Expected: (203 * 100000) / (76 * 3600) ≈ 74.2 cm/s
    assert 74.0 < engine.v_scale_cms < 75.0
    
    # Check wheel radius conversion
    assert 0.01320 < engine.wheel_radius < 0.01330
    
    # Check encoder setup
    assert engine.encoder_segments == 12


def test_speed_to_regulator_zero():
    """
    Tests speed-to-regulator conversion for zero speed.
    
    Why: Zero speed must return 0% regulator to close valve.
    
    Safety: Prevents steam admission when stopped.
    """
    cv = {39: 203, 40: 76, 37: 1325, 38: 12}
    engine = PhysicsEngine(cv)
    
    assert engine.speed_to_regulator(0) == 0.0


def test_speed_to_regulator_linear():
    """
    Tests linear mapping of DCC speed to regulator percentage.
    
    Why: Validates proportional control across speed range.
    """
    cv = {39: 203, 40: 76, 37: 1325, 38: 12}
    engine = PhysicsEngine(cv)
    
    # Half speed should be ~50%
    assert 49.0 < engine.speed_to_regulator(64) < 51.0
    
    # Full speed should be 100%
    assert 99.0 < engine.speed_to_regulator(127) < 100.1


def test_speed_to_regulator_boundary():
    """
    Tests edge cases for speed conversion.
    
    Why: Boundary conditions often expose bugs.
    
    Safety: Ensures valid output for all DCC speed commands.
    """
    cv = {39: 203, 40: 76, 37: 1325, 38: 12}
    engine = PhysicsEngine(cv)
    
    # Speed step 1 should be small but non-zero
    assert 0.0 < engine.speed_to_regulator(1) < 1.0
    
    # Max speed
    assert engine.speed_to_regulator(127) <= 100.0


def test_calc_velocity_zero_time():
    """
    Tests velocity calculation with zero time delta.
    
    Why: Division by zero must be handled safely.
    
    Safety: Returns 0.0 instead of crashing.
    """
    cv = {39: 203, 40: 76, 37: 1325, 38: 12}
    engine = PhysicsEngine(cv)
    
    velocity = engine.calc_velocity(10, 0)
    assert velocity == 0.0


def test_calc_velocity_normal():
    """
    Tests velocity calculation with typical encoder deltas.
    
    Why: Validates odometry math for motion tracking.
    """
    cv = {39: 203, 40: 76, 37: 1325, 38: 12}
    engine = PhysicsEngine(cv)
    
    # 12 ticks in 1 second = 1 full wheel rotation
    velocity = engine.calc_velocity(12, 1000)
    
    # Expected: circumference * 100 (m to cm)
    # Circumference = 2 * pi * 0.01325 ≈ 0.0832 m
    # Velocity ≈ 8.32 cm/s
    assert 8.0 < velocity < 9.0


def test_calc_velocity_negative_time():
    """
    Tests velocity calculation gracefully handles negative time.
    
    Why: Edge case that could occur due to timer rollover.
    
    Safety: Should not crash or produce invalid results.
    """
    cv = {39: 203, 40: 76, 37: 1325, 38: 12}
    engine = PhysicsEngine(cv)
    
    # Negative time should be treated as zero or very small
    velocity = engine.calc_velocity(5, -100)
    assert velocity >= 0.0  # Should not be negative


def test_different_scale_ratios():
    """
    Tests engine works with different model scales.
    
    Why: System should support HO (1:87), OO (1:76), and G (1:22.5) scales.
    """
    # Test HO scale (1:87)
    cv_ho = {39: 203, 40: 87, 37: 1150, 38: 12}
    engine_ho = PhysicsEngine(cv_ho)
    assert engine_ho.v_scale_cms > 0
    
    # Test G scale (1:22.5)
    cv_g = {39: 203, 40: 22.5, 37: 4400, 38: 24}
    engine_g = PhysicsEngine(cv_g)
    assert engine_g.v_scale_cms > engine_ho.v_scale_cms  # G scale should be faster


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-W', 'error'])

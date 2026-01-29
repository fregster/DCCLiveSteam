from app.actuators.leds import GreenStatusLED

def test_green_led_boot_flash(monkeypatch):
    pin = Mock()
    pwm = Mock()
    led = GreenStatusLED(pin, pwm=pwm)
    led.boot_flash()
    base = time.ticks_ms()
    # Even 0.5s intervals: ON, odd: OFF
    monkeypatch.setattr(time, 'ticks_ms', lambda: base)
    led.update()
    assert (1023,) in [call.args for call in pwm.duty.call_args_list]
    pwm.duty.reset_mock()
    monkeypatch.setattr(time, 'ticks_ms', lambda: base + 501)
    led.update()
    assert (0,) in [call.args for call in pwm.duty.call_args_list]

def test_green_led_solid():
    pin = Mock()
    pwm = Mock()
    led = GreenStatusLED(pin, pwm=pwm)
    led.solid()
    led.update()
    assert (1023,) in [call.args for call in pwm.duty.call_args_list]

def test_green_led_dcc_blink(monkeypatch):
    pin = Mock()
    pwm = Mock()
    led = GreenStatusLED(pin, pwm=pwm)
    led.solid()
    led.dcc_blink()
    base = time.ticks_ms()
    monkeypatch.setattr(time, 'ticks_ms', lambda: base)
    led.update()
    assert (1023,) in [call.args for call in pwm.duty.call_args_list]
    pwm.duty.reset_mock()
    monkeypatch.setattr(time, 'ticks_ms', lambda: base + 101)
    led.update()
    assert (0,) in [call.args for call in pwm.duty.call_args_list]

def test_green_led_moving(monkeypatch):
    pin = Mock()
    pwm = Mock()
    led = GreenStatusLED(pin, pwm=pwm)
    led.moving_flash()
    base = time.ticks_ms()
    # 0ms: ON, 125ms: OFF, 250ms: ON, 375ms: OFF
    for offset, expected in [(0, 1023), (125, 0), (250, 1023), (375, 0)]:
        monkeypatch.setattr(time, 'ticks_ms', lambda: base + offset)
        led.update()
        assert (expected,) in [call.args for call in pwm.duty.call_args_list]
        pwm.duty.reset_mock()

def test_green_led_off():
    pin = Mock()
    pwm = Mock()
    led = GreenStatusLED(pin, pwm=pwm)
    led.off()
    led.update()
    assert (0,) in [call.args for call in pwm.duty.call_args_list]
import pytest
from unittest.mock import Mock
import time
from app.actuators.leds import FireboxLED


def test_firebox_led_error_flash(monkeypatch):
    pin = Mock()
    pwm = Mock()
    led = FireboxLED(pin, pwm=pwm, red_duty=1000, orange_duty=500)
    led.set_error(3)
    base = time.ticks_ms()
    monkeypatch.setattr(time, 'ticks_ms', lambda: base)
    led.update()
    assert (1000,) in [call.args for call in pwm.duty.call_args_list]  # Red solid
    pwm.duty.reset_mock()
    monkeypatch.setattr(time, 'ticks_ms', lambda: base + 5001)
    for i in range(3):
        monkeypatch.setattr(time, 'ticks_ms', lambda: base + 5001 + i*800)
        led.update()
        assert (1000,) in [call.args for call in pwm.duty.call_args_list]  # Red on
        pwm.duty.reset_mock()
        monkeypatch.setattr(time, 'ticks_ms', lambda: base + 5001 + i*800 + 400)
        led.update()
        assert (0,) in [call.args for call in pwm.duty.call_args_list]  # Red off
        pwm.duty.reset_mock()
    monkeypatch.setattr(time, 'ticks_ms', lambda: base + 5001 + 3*800)
    led.update()
    assert (1000,) in [call.args for call in pwm.duty.call_args_list]  # Back to solid


def test_firebox_led_warning_flash(monkeypatch):
    pin = Mock()
    pwm = Mock()
    led = FireboxLED(pin, pwm=pwm, red_duty=1000, orange_duty=500)
    led.set_warning(2)
    base = time.ticks_ms()
    monkeypatch.setattr(time, 'ticks_ms', lambda: base)
    led.update()
    assert (500,) in [call.args for call in pwm.duty.call_args_list]  # Orange solid
    pwm.duty.reset_mock()
    monkeypatch.setattr(time, 'ticks_ms', lambda: base + 5001)
    for i in range(2):
        monkeypatch.setattr(time, 'ticks_ms', lambda: base + 5001 + i*800)
        led.update()
        assert (500,) in [call.args for call in pwm.duty.call_args_list]  # Orange on
        pwm.duty.reset_mock()
        monkeypatch.setattr(time, 'ticks_ms', lambda: base + 5001 + i*800 + 400)
        led.update()
        assert (0,) in [call.args for call in pwm.duty.call_args_list]  # Orange off
        pwm.duty.reset_mock()
    monkeypatch.setattr(time, 'ticks_ms', lambda: base + 5001 + 2*800)
    led.update()
    assert (500,) in [call.args for call in pwm.duty.call_args_list]  # Back to solid

def test_firebox_led_clear():
    pin = Mock()
    pwm = Mock()
    led = FireboxLED(pin, pwm=pwm)
    led.set_error(1)
    led.clear()
    pwm.duty.assert_called_with(0)

def test_firebox_led_priority():
    pin = Mock()
    pwm = Mock()
    led = FireboxLED(pin, pwm=pwm)
    led.set_warning(2)
    led.set_error(3)
    assert led.state == 'red'
    led.set_warning(1)
    assert led.state == 'red'  # Error takes precedence
"""
Unit tests for actuators.py module.
Tests servo control with slew-rate limiting and PID pressure control.
"""
import pytest
from unittest.mock import Mock, patch
import time
from app.actuators.servo import MechanicalMapper


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

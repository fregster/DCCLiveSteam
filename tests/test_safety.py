"""
Unit tests for safety.py module.
Tests watchdog monitoring, degradation mode, and emergency shutdown triggers.
"""
import pytest
from unittest.mock import Mock, MagicMock
from app.safety import Watchdog, DegradedModeController
import time


@pytest.fixture
def watchdog():
    """Creates a fresh Watchdog instance for each test."""
    return Watchdog()


@pytest.fixture
def mock_loco():
    """Creates a mock Mallard instance."""
    loco = Mock()
    loco.die = Mock()
    return loco


@pytest.fixture
def safe_cv():
    """Returns CV table with reasonable safety limits."""
    return {
        41: 75,   # Logic temp limit (°C)
        42: 110,  # Boiler temp limit (°C)
        43: 250,  # Superheater temp limit (°C)
        44: 20,   # DCC timeout (x100ms)
        45: 8,    # Power timeout (x100ms)
        88: 20    # Degraded mode timeout (seconds)
    }


def test_watchdog_initialization(watchdog):
    """
    Tests Watchdog initializes timer references.
    
    Why: Timers must start at boot to track signal timeouts.
    
    Safety: Ensures timeout detection is ready from first loop.
    """
    assert watchdog.pwr_t >= 0
    assert watchdog.dcc_t >= 0


def test_watchdog_normal_operation(watchdog, mock_loco, safe_cv):
    """
    Tests watchdog passes with all parameters in safe range.
    
    Why: Normal operation should not trigger shutdown.
    """
    watchdog.check(
        t_logic=50,      # Well below 75°C limit
        t_boiler=85,     # Well below 110°C limit
        t_super=180,     # Well below 250°C limit
        track_v=15000,   # Above 1500mV threshold
        dcc_active=True,
        cv=safe_cv,
        loco=mock_loco
    )
    
    mock_loco.die.assert_not_called()


def test_watchdog_logic_overheat(watchdog, mock_loco, safe_cv):
    """
    Tests watchdog triggers on logic bay overheating.
    
    Why: TinyPICO thermal protection prevents silicon damage.
    
    Safety: Must shutdown before ESP32 enters thermal throttling.
    """
    watchdog.check(
        t_logic=80,      # Exceeds 75°C limit
        t_boiler=85,
        t_super=180,
        track_v=15000,
        dcc_active=True,
        cv=safe_cv,
        loco=mock_loco
    )
    
    mock_loco.die.assert_called_once_with("LOGIC_HOT")


def test_watchdog_dry_boil(watchdog, mock_loco, safe_cv):
    """
    Tests watchdog triggers on dry-boil condition.
    
    Why: Boiler without water will overheat and fail catastrophically.
    
    Safety: CRITICAL - prevents boiler rupture and injury.
    """
    watchdog.check(
        t_logic=50,
        t_boiler=115,    # Exceeds 110°C limit
        t_super=180,
        track_v=15000,
        dcc_active=True,
        cv=safe_cv,
        loco=mock_loco
    )
    
    mock_loco.die.assert_called_once_with("DRY_BOIL")


def test_watchdog_superheater_overheat(watchdog, mock_loco, safe_cv):
    """
    Tests watchdog triggers on superheater overheating.
    
    Why: Excessive superheat damages steam pipes and gaskets.
    
    Safety: Protects mechanical integrity of steam system.
    """
    watchdog.check(
        t_logic=50,
        t_boiler=85,
        t_super=260,     # Exceeds 250°C limit
        track_v=15000,
        dcc_active=True,
        cv=safe_cv,
        loco=mock_loco
    )
    
    mock_loco.die.assert_called_once_with("SUPER_HOT")


def test_watchdog_power_loss(watchdog, mock_loco, safe_cv):
    """
    Tests watchdog triggers on sustained power loss.
    
    Why: Track power loss requires secured stop before supercap dies.
    
    Safety: Ensures controlled shutdown with remaining power.
    """
    from unittest.mock import patch
    
    with patch('app.safety.time') as mock_time:
        # Simulate ticks_ms() returning elapsed time: 0ms then 1000ms later
        mock_time.ticks_ms.side_effect = [0, 1000]
        # Mock ticks_diff to return time difference
        mock_time.ticks_diff.side_effect = lambda new, old: new - old
        
        # First check establishes baseline
        watchdog.check(
            t_logic=50,
            t_boiler=85,
            t_super=180,
            track_v=1000,    # Below 1500mV threshold
            dcc_active=True,
            cv=safe_cv,
            loco=mock_loco
        )
        
        mock_loco.die.assert_not_called()  # Not enough time elapsed
        
        # Simulate timeout passage (CV45 * 100ms = 800ms, we simulate 1000ms)
        watchdog.check(
            t_logic=50,
            t_boiler=85,
            t_super=180,
            track_v=1000,
            dcc_active=True,
            cv=safe_cv,
            loco=mock_loco
        )
        
        mock_loco.die.assert_called_with("PWR_LOSS")


def test_watchdog_dcc_signal_loss(watchdog, mock_loco, safe_cv):
    """
    Tests watchdog triggers on DCC signal timeout.
    
    Why: Lost radio/track signal requires safe stop.
    
    Safety: Prevents runaway if control link fails.
    """
    from unittest.mock import patch
    
    with patch('app.safety.time') as mock_time:
        # Simulate ticks_ms() returning elapsed time: 0ms then 2200ms later
        mock_time.ticks_ms.side_effect = [0, 2200]
        # Mock ticks_diff to return time difference
        mock_time.ticks_diff.side_effect = lambda new, old: new - old
        
        # First check with active DCC
        watchdog.check(
            t_logic=50,
            t_boiler=85,
            t_super=180,
            track_v=15000,
            dcc_active=False,  # Signal lost
            cv=safe_cv,
            loco=mock_loco
        )
        
        mock_loco.die.assert_not_called()
        
        # Simulate timeout passage (CV44 * 100ms = 2000ms, we simulate 2200ms)
        watchdog.check(
            t_logic=50,
            t_boiler=85,
            t_super=180,
            track_v=15000,
            dcc_active=False,
            cv=safe_cv,
            loco=mock_loco
        )
        
        mock_loco.die.assert_called_with("DCC_LOST")


def test_watchdog_power_recovery_resets_timer(watchdog, mock_loco, safe_cv):
    """
    Tests that power recovery resets timeout timer.
    
    Why: Brief power drops should not accumulate into timeout.
    """
    from unittest.mock import patch
    
    with patch('app.safety.time') as mock_time:
        # Simulate ticks_ms() progression: 0ms → 500ms → 600ms → 1100ms
        mock_time.ticks_ms.side_effect = [0, 500, 600, 1100]
        # Mock ticks_diff to return time difference
        mock_time.ticks_diff.side_effect = lambda new, old: new - old
        
        # Drop power briefly
        watchdog.check(
            t_logic=50, t_boiler=85, t_super=180,
            track_v=1000, dcc_active=True, cv=safe_cv, loco=mock_loco
        )
        
        # Simulate 500ms passing with power lost
        watchdog.check(
            t_logic=50, t_boiler=85, t_super=180,
            track_v=1000, dcc_active=True, cv=safe_cv, loco=mock_loco
        )
        
        # Power restored at 600ms (timer resets)
        watchdog.check(
            t_logic=50, t_boiler=85, t_super=180,
            track_v=15000, dcc_active=True, cv=safe_cv, loco=mock_loco
        )
        
        # Now at 1100ms - 600ms reset = 500ms elapsed since recovery (under 800ms limit)
        watchdog.check(
            t_logic=50, t_boiler=85, t_super=180,
            track_v=15000, dcc_active=True, cv=safe_cv, loco=mock_loco
        )
        
        mock_loco.die.assert_not_called()  # Timer was reset


def test_watchdog_multiple_simultaneous_faults(watchdog, mock_loco, safe_cv):
    """
    Tests that first detected fault wins in multi-fault scenario.
    
    Why: Emergency shutdown sequence runs only once.
    
    Safety: Any single fault is sufficient to trigger shutdown.
    """
    watchdog.check(
        t_logic=80,      # FAULT
        t_boiler=115,    # FAULT
        t_super=260,     # FAULT
        track_v=15000,
        dcc_active=True,
        cv=safe_cv,
        loco=mock_loco
    )
    
    # Should call die() exactly once (for first detected fault)
    assert mock_loco.die.call_count == 1


# NEW: Degraded Mode Tests

def test_watchdog_initialization_degraded_mode(watchdog):
    """
    Tests watchdog initializes degradation state variables.
    
    Why: Degraded mode tracking must start in NOMINAL state.
    """
    assert watchdog.mode == "NOMINAL"
    assert watchdog.degraded_start_time is None
    assert watchdog.is_degraded() is False
    assert watchdog.is_critical() is False


def test_watchdog_sensor_health_single_failure(watchdog, safe_cv):
    """
    Tests watchdog transitions to DEGRADED on single sensor failure.
    
    Why: Single sensor failure should not trigger immediate shutdown.
    """
    mock_sensors = Mock()
    mock_sensors.failed_sensor_count = 1
    mock_sensors.failure_reason = "boiler_temp failed"
    
    watchdog.check_sensor_health(mock_sensors, safe_cv)
    
    assert watchdog.mode == "DEGRADED"
    assert watchdog.is_degraded() is True
    assert watchdog.degraded_start_time is not None


def test_watchdog_sensor_health_multiple_failures(watchdog, safe_cv):
    """
    Tests watchdog transitions to CRITICAL on multiple sensor failures.
    
    Why: Multiple failures → immediate emergency shutdown (don't wait for decel).
    """
    mock_sensors = Mock()
    mock_sensors.failed_sensor_count = 2
    mock_sensors.failure_reason = "boiler_temp and logic_temp failed"
    
    watchdog.check_sensor_health(mock_sensors, safe_cv)
    
    assert watchdog.mode == "CRITICAL"
    assert watchdog.is_critical() is True


def test_watchdog_sensor_recovery_from_degraded(watchdog, safe_cv):
    """
    Tests watchdog recovers to NOMINAL when sensor fixed.
    
    Why: Glitch recovery should reset state to normal monitoring.
    """
    mock_sensors = Mock()
    
    # Enter degraded mode
    mock_sensors.failed_sensor_count = 1
    watchdog.check_sensor_health(mock_sensors, safe_cv)
    assert watchdog.is_degraded() is True
    
    # Sensor recovers
    mock_sensors.failed_sensor_count = 0
    watchdog.check_sensor_health(mock_sensors, safe_cv)
    assert watchdog.mode == "NOMINAL"
    assert watchdog.degraded_start_time is None


def test_watchdog_degraded_mode_timeout(watchdog, safe_cv):
    """
    Tests watchdog times out in DEGRADED mode after CV88 seconds.
    
    Why: If deceleration takes too long, force shutdown.
    """
    mock_sensors = Mock()
    mock_sensors.failed_sensor_count = 1
    
    # Enter degraded mode
    watchdog.check_sensor_health(mock_sensors, safe_cv)
    assert watchdog.is_degraded() is True
    
    # Manually set start time to trigger timeout
    # CV88 default is 20 seconds
    watchdog.degraded_start_time = time.time() - 25  # 25 seconds ago
    
    # Check again - should timeout
    watchdog.check_sensor_health(mock_sensors, safe_cv)
    assert watchdog.mode == "CRITICAL"


def test_watchdog_check_skips_thermal_in_degraded(watchdog, mock_loco, safe_cv):
    """
    Tests that thermal checks are skipped when DEGRADED.
    
    Why: In DEGRADED mode, use cached sensor values (can't trust readings).
    """
    # Enter degraded mode
    watchdog.mode = "DEGRADED"
    
    # Even with extremely high temps, shouldn't trigger shutdown in DEGRADED
    watchdog.check(
        t_logic=150,     # Way above 75°C limit!
        t_boiler=200,    # Way above 110°C limit!
        t_super=300,     # Way above 250°C limit!
        track_v=15000,   # Power OK
        dcc_active=True, # DCC OK
        cv=safe_cv,
        loco=mock_loco
    )
    
    # Should NOT trigger LOGIC_HOT, DRY_BOIL, or SUPER_HOT
    # (Signal checks still work, so DCC/Power failsafes active)
    assert not mock_loco.die.called or "LOGIC_HOT" not in str(mock_loco.die.call_args)


def test_watchdog_check_critical_triggers_shutdown(watchdog, mock_loco, safe_cv):
    """
    Tests CRITICAL mode triggers immediate shutdown.
    
    Why: Multiple sensor failures = immediate safety shutdown.
    """
    watchdog.mode = "CRITICAL"
    
    watchdog.check(
        t_logic=50,
        t_boiler=85,
        t_super=180,
        track_v=15000,
        dcc_active=True,
        cv=safe_cv,
        loco=mock_loco
    )
    
    mock_loco.die.assert_called_with("MULTIPLE_SENSORS_FAILED")


# DegradedModeController Tests

@pytest.fixture
def degraded_controller():
    """Creates a DegradedModeController with test CV table."""
    cv = {87: 10.0}  # 10 cm/s² deceleration rate
    return DegradedModeController(cv)


def test_degraded_controller_initialization(degraded_controller):
    """Tests DegradedModeController initializes correctly."""
    assert degraded_controller.degraded_decel_rate_cms2 == 10.0
    assert degraded_controller.is_decelerating is False
    assert degraded_controller.decel_start_time is None


def test_degraded_controller_start_deceleration(degraded_controller):
    """Tests starting deceleration from current speed."""
    degraded_controller.start_deceleration(50.0)
    
    assert degraded_controller.is_decelerating is True
    assert degraded_controller.current_commanded_speed_cms == 50.0
    assert degraded_controller.decel_start_time is not None


def test_degraded_controller_speed_reduction(degraded_controller):
    """Tests speed reduces at correct rate."""
    degraded_controller.start_deceleration(50.0)
    
    # Immediate speed (t=0)
    speed_0 = degraded_controller.update_speed_command()
    assert abs(speed_0 - 50.0) < 0.5  # Very close to initial
    
    # After a short time, speed should have reduced slightly
    # The 10 cm/s² deceleration should reduce speed
    degraded_controller.decel_start_time = time.time() - 0.5  # 0.5s elapsed
    speed_half = degraded_controller.update_speed_command()
    
    # Speed reduction = 10 cm/s² × 0.5s = 5 cm/s reduction
    expected_half = 50.0 - 5.0
    assert 44.0 < speed_half < 46.0, f"Expected ~45, got {speed_half}"


def test_degraded_controller_never_negative(degraded_controller):
    """Tests speed never goes negative during deceleration."""
    degraded_controller.start_deceleration(5.0)
    
    # Force time forward to simulate long deceleration
    degraded_controller.decel_start_time = time.time() - 10.0  # 10 seconds ago
    
    speed = degraded_controller.update_speed_command()
    assert speed >= 0.0


def test_degraded_controller_is_stopped(degraded_controller):
    """Tests is_stopped() detection."""
    degraded_controller.start_deceleration(5.0)
    
    # Initially not stopped
    assert degraded_controller.is_stopped() is False
    
    # Force time forward to complete decel
    degraded_controller.decel_start_time = time.time() - 5.0
    
    # Should be stopped now
    assert degraded_controller.is_stopped() is True


def test_degraded_controller_zero_speed(degraded_controller):
    """Tests deceleration to zero from various speeds."""
    test_speeds = [10.0, 30.0, 60.0, 100.0]
    
    for initial_speed in test_speeds:
        degraded_controller.start_deceleration(initial_speed)
        degraded_controller.decel_start_time = time.time() - 20.0  # Force complete decel
        
        final_speed = degraded_controller.update_speed_command()
        assert final_speed == 0.0, f"Failed for initial speed {initial_speed}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-W', 'error'])

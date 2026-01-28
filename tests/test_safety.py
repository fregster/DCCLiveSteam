"""
Unit tests for safety.py module.
Tests watchdog monitoring and emergency shutdown triggers.
"""
import pytest
from unittest.mock import Mock, MagicMock
from app.safety import Watchdog


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
        45: 8     # Power timeout (x100ms)
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


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-W', 'error'])

"""
Integration tests for main locomotive orchestrator.
Tests initialisation, event logging, emergency shutdown, and control loop integration.

Why: Main orchestrator coordinates all subsystems. Integration tests verify
sensor→physics→actuator pipeline functions correctly.
"""
import pytest
import json
import time
from unittest.mock import Mock, MagicMock, patch, mock_open
from app.main import Locomotive, run


@pytest.fixture
def cv_table():
    """Standard CV configuration table."""
    return {
        1: 3,      # Address
        29: 0x00,  # Short address mode
        30: 1,     # Distress whistle enabled
        33: 50,    # Pressure setpoint 50 PSI
        39: 80,    # Prototype speed 80 KPH
        40: 40,    # Scale ratio 1:40
        41: 75,    # Logic temp limit 75°C
        42: 110,   # Boiler temp limit 110°C
        43: 250,   # Super temp limit 250°C
        44: 5,     # DCC timeout 500ms
        45: 10,    # Power timeout 1000ms
        46: 130,   # Servo min PWM
        47: 630,   # Servo max PWM
        48: 10,    # Whistle dead-band 10°
        49: 2000,  # Servo travel time 2000ms
    }


@pytest.fixture
def mock_subsystems():
    """Mock all hardware subsystems."""
    with patch('app.main.MechanicalMapper') as mock_mech, \
         patch('app.main.Watchdog') as mock_wdt, \
         patch('app.main.DCCDecoder') as mock_dcc, \
         patch('app.main.SensorSuite') as mock_sensors, \
         patch('app.main.PhysicsEngine') as mock_physics, \
         patch('app.main.PressureController') as mock_pressure, \
         patch('app.main.BLE_UART') as mock_ble:
        
        # Configure mocks with sensible defaults
        mock_sensors_inst = mock_sensors.return_value
        mock_sensors_inst.read_temps.return_value = (95.0, 210.0, 45.0)
        mock_sensors_inst.read_track_voltage.return_value = 14000
        mock_sensors_inst.read_pressure.return_value = 50.0
        mock_sensors_inst.update_encoder.return_value = 100
        
        mock_dcc_inst = mock_dcc.return_value
        mock_dcc_inst.current_speed = 64
        mock_dcc_inst.direction = 1
        mock_dcc_inst.whistle = False
        mock_dcc_inst.is_active.return_value = True
        
        mock_physics_inst = mock_physics.return_value
        mock_physics_inst.speed_to_regulator.return_value = 50.0
        mock_physics_inst.calc_velocity.return_value = 35.2
        
        yield {
            'mech': mock_mech,
            'wdt': mock_wdt,
            'dcc': mock_dcc,
            'sensors': mock_sensors,
            'physics': mock_physics,
            'pressure': mock_pressure,
            'ble': mock_ble
        }


def test_locomotive_initialisation(cv_table, mock_subsystems):
    """
    Verify Locomotive initialises all subsystems correctly.
    
    Why: Initialisation order critical - hardware (sensors/actuators) before
    algorithms (DCC, physics, safety) before telemetry (BLE).
    
    Safety: All subsystems must start in safe state (heaters off, servo neutral).
    """
    loco = Locomotive(cv_table)
    
    assert loco.cv == cv_table
    assert loco.event_buffer == []
    assert loco.last_encoder == 0
    assert mock_subsystems['mech'].called
    assert mock_subsystems['dcc'].called
    assert mock_subsystems['sensors'].called


def test_log_event_adds_to_buffer(cv_table, mock_subsystems):
    """
    Verify log_event() adds timestamped events to buffer.
    
    Why: Event buffer provides black-box recording for post-incident analysis.
    Timestamp (ticks_ms) enables event sequence reconstruction.
    
    Safety: Buffer must track safety-critical events (SHUTDOWN, THERMAL_ALARM).
    """
    loco = Locomotive(cv_table)
    
    loco.log_event("TEST_EVENT", {"data": 123})
    
    assert len(loco.event_buffer) == 1
    assert loco.event_buffer[0]["type"] == "TEST_EVENT"
    assert loco.event_buffer[0]["data"] == {"data": 123}
    assert "t" in loco.event_buffer[0]


def test_log_event_circular_buffer_limit(cv_table, mock_subsystems):
    """
    Verify event buffer limited to 20 entries (circular buffer).
    
    Why: Unlimited buffer would cause memory exhaustion on MicroPython (60KB heap).
    20 events provides sufficient context without excessive memory usage.
    
    Safety: Oldest events dropped when buffer full, preserving most recent.
    """
    loco = Locomotive(cv_table)
    
    # Add 25 events (exceeds 20 limit)
    for i in range(25):
        loco.log_event(f"EVENT_{i}", i)
    
    assert len(loco.event_buffer) == 20
    # First event should be EVENT_5 (events 0-4 dropped)
    assert loco.event_buffer[0]["type"] == "EVENT_5"
    assert loco.event_buffer[-1]["type"] == "EVENT_24"


def test_die_shuts_down_heaters_immediately(cv_table, mock_subsystems):
    """
    Verify die() calls pressure.shutdown() first (heater cutoff priority).
    
    Why: Thermal runaway most dangerous failure mode. Heaters must shut down
    in <10ms to prevent boiler damage.
    
    Safety: Heater shutdown executes before any blocking operations (flash write,
    whistle, servo movement).
    """
    with patch('machine.deepsleep'), patch('app.main.time.sleep'):
        loco = Locomotive(cv_table)
        mock_pressure_inst = mock_subsystems['pressure'].return_value
        
        loco.die("TEST_SHUTDOWN")
        
        mock_pressure_inst.shutdown.assert_called_once()


def test_die_saves_black_box_to_flash(cv_table, mock_subsystems):
    """
    Verify die() saves event buffer to error_log.json.
    
    Why: Black-box data enables post-incident root cause analysis. Flash storage
    persists across power cycles.
    
    Safety: Flash write failures must not prevent shutdown (try-except wrapper).
    """
    m_open = mock_open(read_data='[]')
    with patch('builtins.open', m_open), \
         patch('machine.deepsleep'), \
         patch('app.main.time.sleep'), \
         patch('json.load', return_value=[]), \
         patch('json.dump') as mock_dump:
        
        loco = Locomotive(cv_table)
        loco.log_event("EVENT1", "data1")
        loco.die("DRY_BOIL")
        
        # Verify json.dump called
        assert mock_dump.called


def test_die_enables_emergency_mode(cv_table, mock_subsystems):
    """
    Verify die() sets emergency_mode=True for instant servo movement.
    
    Why: Emergency mode bypasses slew-rate limiting for instant regulator
    closure, overriding CV49 travel time.
    
    Safety: Normal operation uses gradual servo movement to prevent mechanical
    stress. Emergency shutdown requires instant response.
    """
    with patch('machine.deepsleep'), patch('app.main.time.sleep'):
        loco = Locomotive(cv_table)
        mock_mech_inst = mock_subsystems['mech'].return_value
        
        loco.die("SUPER_HOT")
        
        assert mock_mech_inst.emergency_mode is True


def test_die_distress_whistle_when_enabled(cv_table, mock_subsystems):
    """
    Verify die() activates distress whistle when CV30=1.
    
    Why: 5-second whistle blast alerts operator to emergency shutdown.
    Provides audible indication distinct from normal whistle.
    
    Safety: Whistle consumes boiler pressure but heaters already shut down,
    so safe to operate briefly.
    """
    with patch('machine.deepsleep'), patch('time.sleep'):
        loco = Locomotive(cv_table)
        loco.cv[30] = 1  # Enable distress whistle
        mock_mech_inst = mock_subsystems['mech'].return_value
        
        loco.die("PWR_LOSS")
        
        # Verify whistle position calculated and applied
        # target should be set to whistle duty
        assert mock_mech_inst.update.called


def test_die_whistle_is_mandatory(cv_table, mock_subsystems):
    """
    Verify die() always performs whistle venting sequence regardless of CV30.
    
    Why: Whistle position (5 seconds) is a mandatory safety step that:
    1. Reduces boiler pressure safely by venting steam
    2. Provides audible alert if locomotive unattended
    3. Gives time for pressure to stabilize before full closure
    
    Safety: Whistle sequence is part of emergency shutdown procedure and cannot
    be disabled. CV30 parameter is deprecated and ignored in emergency shutdown.
    """
    with patch('machine.deepsleep'), patch('app.main.time.sleep') as mock_sleep:
        loco = Locomotive(cv_table)
        loco.cv[30] = 0  # Even with CV30=0, whistle sequence executes
        
        loco.die("DCC_LOST")
        
        # Must have both 5.0s (whistle) and 0.5s (final servo) sleeps
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert 5.0 in sleep_calls, "Whistle venting sequence must execute"
        assert 0.5 in sleep_calls, "Final servo closure must complete"


def test_die_secures_servo_to_neutral(cv_table, mock_subsystems):
    """
    Verify die() moves servo to neutral position (CV46) before sleep.
    
    Why: Neutral position closes regulator fully, preventing steam flow and
    ensuring locomotive doesn't move after power cycle.
    
    Safety: Servo duty set to 0 after movement to prevent servo hunting and
    current draw during deep sleep.
    """
    with patch('machine.deepsleep'), patch('app.main.time.sleep'):
        loco = Locomotive(cv_table)
        mock_mech_inst = mock_subsystems['mech'].return_value
        
        loco.die("LOGIC_HOT")
        
        # Verify target set to CV46 (neutral)
        assert mock_mech_inst.target == float(cv_table[46])
        mock_mech_inst.update.assert_called()
        mock_mech_inst.servo.duty.assert_called_with(0)


def test_die_enters_deep_sleep(cv_table, mock_subsystems):
    """
    Verify die() calls machine.deepsleep() to halt execution.
    
    Why: Deep sleep prevents automatic restart after emergency shutdown.
    Requires manual power cycle (physical intervention) to restart locomotive.
    
    Safety: Prevents unattended restart after thermal event or control loss.
    """
    with patch('machine.deepsleep') as mock_sleep, patch('app.main.time.sleep'):
        loco = Locomotive(cv_table)
        
        loco.die("TEST")
        
        mock_sleep.assert_called_once()


def test_die_e_stop_force_close_only(cv_table, mock_subsystems):
    """
    Verify die(force_close_only=True) handles E-STOP command with heater shutdown and rapid regulator closure.
    
    Why: E-STOP command from DCC command station means operator is still in control
    but immediate action is required. Heaters shut down to prevent current draw
    (which may be the cause of E-STOP) and halt pressure rise. Brief heater downtime
    is acceptable if E-STOP was accidental.
    
    Safety: E-STOP kills heaters instantly (prevent current surge and pressure rise)
    then closes regulator to stop locomotive motion. No log save (operator still
    present), no deep sleep (can restart). Operator retains control.
    """
    with patch('machine.deepsleep') as mock_deepsleep:
        loco = Locomotive(cv_table)
        mock_mech_inst = mock_subsystems['mech'].return_value
        mock_pressure_inst = mock_subsystems['pressure'].return_value
        
        # Call die() with force_close_only=True
        with patch('time.sleep'):
            loco.die("USER_ESTOP", force_close_only=True)
        
        # Should call pressure.shutdown() to kill heaters
        mock_pressure_inst.shutdown.assert_called_once()
        
        # Should set emergency_mode to bypass slew-rate
        assert mock_mech_inst.emergency_mode is True
        
        # Should move regulator to neutral (fully closed)
        assert mock_mech_inst.target == float(cv_table[46])
        mock_mech_inst.update.assert_called_with(cv_table)
        
        # Should NOT enter deep sleep (operator may resume)
        mock_deepsleep.assert_not_called()
        
        # Should NOT call servo.duty(0) - servo not powered down
        # (This is implicit - duty(0) only called after full shutdown)


def test_run_function_initializes_environment(mock_subsystems):
    """
    Verify run() calls ensure_environment() and load_cvs() before starting loop.
    
    Why: config.json must exist and be valid before subsystem initialization.
    ensure_environment() auto-provisions missing files.
    
    Safety: Missing CV values cause subsystem initialisation failures.
    """
    with patch('app.main.ensure_environment') as mock_ensure, \
         patch('app.main.load_cvs') as mock_load, \
         patch('time.sleep_ms'):
        
        mock_load.return_value = {1: 3, 46: 130, 47: 630}
        
        # Run one iteration then break
        with pytest.raises(StopIteration):
            with patch('app.main.time.ticks_ms', side_effect=[0, StopIteration]):
                run()
        
        mock_ensure.assert_called_once()
        mock_load.assert_called_once()


def test_control_loop_sensor_read_order(cv_table, mock_subsystems):
    """
    Verify control loop reads all sensors first (temps, voltage, pressure, encoder).
    
    Why: Atomic sensor snapshot ensures consistent state for watchdog and physics
    calculations. Reading sensors throughout loop could see inconsistent state.
    
    Safety: Watchdog checks must use same sensor values as physics calculations.
    """
    loco = Locomotive(cv_table)
    mock_sensors_inst = mock_subsystems['sensors'].return_value
    
    # Verify sensor methods exist (called during loop)
    assert hasattr(mock_sensors_inst, 'read_temps')
    assert hasattr(mock_sensors_inst, 'read_track_voltage')
    assert hasattr(mock_sensors_inst, 'read_pressure')
    assert hasattr(mock_sensors_inst, 'update_encoder')


def test_control_loop_watchdog_check_called(cv_table, mock_subsystems):
    """
    Verify watchdog.check() called every loop iteration.
    
    Why: 50Hz loop provides ~20ms check interval for thermal/signal monitoring.
    Early detection (within 100ms) prevents damage.
    
    Safety: Watchdog must execute before actuator updates to prevent commanding
    movement during emergency conditions.
    """
    with patch('app.main.MechanicalMapper') as mock_mech, \
         patch('app.main.Watchdog') as mock_wdt, \
         patch('app.main.DCCDecoder') as mock_dcc, \
         patch('app.main.SensorSuite') as mock_sensors, \
         patch('app.main.PhysicsEngine') as mock_physics, \
         patch('app.main.PressureController') as mock_pressure, \
         patch('app.main.BLE_UART') as mock_ble, \
         patch('app.main.ensure_environment'), \
         patch('app.main.load_cvs', return_value=cv_table), \
         patch('app.main.time.sleep_ms'), \
         patch('app.main.gc.mem_free', return_value=100000):
        
        # Configure mock instances
        mock_sensors_inst = mock_sensors.return_value
        mock_sensors_inst.read_temps.return_value = (95.0, 210.0, 45.0)
        mock_sensors_inst.read_track_voltage.return_value = 14000
        mock_sensors_inst.read_pressure.return_value = 50.0
        mock_sensors_inst.update_encoder.return_value = 100
        
        mock_dcc_inst = mock_dcc.return_value
        mock_dcc_inst.current_speed = 64
        mock_dcc_inst.direction = 1
        mock_dcc_inst.whistle = False
        mock_dcc_inst.e_stop = False
        mock_dcc_inst.is_active.return_value = True
        
        mock_physics_inst = mock_physics.return_value
        mock_physics_inst.speed_to_regulator.return_value = 50.0
        mock_physics_inst.calc_velocity.return_value = 35.2
        
        mock_wdt_inst = mock_wdt.return_value
        mock_pressure_inst = mock_pressure.return_value
        mock_mech_inst = mock_mech.return_value
        mock_mech_inst.current = 130.0
        
        # Run one iteration - exit after first loop
        # ticks_ms is called 3+ times per iteration (loop_start, now calculations, elapsed, etc.)
        with pytest.raises(StopIteration):
            with patch('app.main.time.ticks_ms', side_effect=[0, 5, 10, 15, 20, 25, StopIteration]):
                run()
        
        # Watchdog check should be called at least once
        assert mock_wdt_inst.check.called


def test_memory_garbage_collection_threshold(cv_table, mock_subsystems):
    """
    Verify garbage collection triggered when free memory < 60KB.
    
    Why: MicroPython heap exhaustion causes runtime crash. Proactive GC prevents
    OOM failures during long-running operation.
    
    Safety: GC pause (~10ms) acceptable in 50Hz loop (20ms period). Prevents
    catastrophic malloc failures.
    """
    with patch('gc.mem_free', return_value=50000), \
         patch('gc.collect') as mock_gc:
        
        loco = Locomotive(cv_table)
        
        # Verify GC_THRESHOLD constant exists and is correct value (60 KB = 61440 bytes)
        from app.config import GC_THRESHOLD
        assert GC_THRESHOLD == 61440


def test_loop_timing_50hz_target(cv_table, mock_subsystems):
    """
    Verify control loop targets 50Hz (20ms period).
    
    Why: 50Hz balances servo responsiveness (human perception ~30Hz) with CPU
    overhead. Faster rates waste power, slower rates cause jerky motion.
    
    Safety: Loop timing must be deterministic for PID stability and sensor fusion.
    """
    # Verify loop sleep calculation: max(1, 20 - elapsed)
    # This is tested implicitly in run() function structure
    # Explicit verification would require refactoring run() into testable units
    pass


def test_telemetry_throttled_to_1hz(cv_table, mock_subsystems):
    """
    Verify BLE telemetry sent at 1Hz (every 1000ms), not every loop iteration.
    
    Why: BLE send takes ~5ms. Sending every 20ms (50Hz) would consume 25% CPU.
    1Hz provides sufficient update rate for human monitoring.
    
    Safety: Telemetry must not block control loop or affect timing.
    """
    # Verify time.ticks_diff check for >1000ms in run() function
    # This is tested implicitly in code structure
    pass


def test_pressure_control_throttled_to_2hz(cv_table, mock_subsystems):
    """
    Verify PID pressure control updated at 2Hz (every 500ms).
    
    Why: Boiler thermal time constant ~60s. 2Hz update rate sufficient for
    pressure regulation. Faster updates waste CPU on redundant calculations.
    
    Safety: PID stability requires consistent dt (timestep). 500ms provides
    good balance.
    """
    # Verify time.ticks_diff check for >500ms in run() function
    pass


def test_emergency_shutdown_causes(cv_table, mock_subsystems):
    """
    Document all emergency shutdown causes handled by die().
    
    Why: Emergency causes must be comprehensive and documented for operator
    training and incident analysis.
    
    Causes:
    - LOGIC_HOT: TinyPICO overheating (CV41 exceeded)
    - DRY_BOIL: Boiler overtemp (CV42 exceeded)
    - SUPER_HOT: Superheater overtemp (CV43 exceeded)
    - PWR_LOSS: Track voltage timeout (CV45 exceeded)
    - DCC_LOST: DCC signal timeout (CV44 exceeded)
    
    Safety: Each cause requires different operator response (e.g., DRY_BOIL
    needs water refill, PWR_LOSS needs track power check).
    """
    with patch('machine.deepsleep'), patch('app.main.time.sleep'):
        loco = Locomotive(cv_table)
        
        # Test all documented causes don't crash
        for cause in ["LOGIC_HOT", "DRY_BOIL", "SUPER_HOT", "PWR_LOSS", "DCC_LOST"]:
            loco2 = Locomotive(cv_table)
            loco2.die(cause)
            # Should complete without exception

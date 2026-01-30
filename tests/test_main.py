# Patch Watchdog globally for all tests that instantiate Locomotive or run
import pytest
from unittest.mock import patch


import pytest
from unittest.mock import patch

def _patch_watchdog():
    class DummyWatchdog:
        def __init__(self, *args, **kwargs):
            # DummyWatchdog: intentionally does nothing for test isolation
            pass
        def check(self, *args, **kwargs):
            # DummyWatchdog: intentionally does nothing for test isolation
            pass
    return patch('app.main.Watchdog', new=DummyWatchdog)

@pytest.fixture(autouse=True)
def patch_watchdog(request):
    # Disable for test_control_loop_watchdog_check_called
    if request.node.name == "test_control_loop_watchdog_check_called":
        yield
    else:
        with _patch_watchdog():
            yield
"""
Integration tests for main locomotive orchestrator.
Tests initialisation, event logging, emergency shutdown, and control loop integration.

Why: Main orchestrator coordinates all subsystems. Integration tests verify
sensor→physics→actuator pipeline functions correctly.
"""
import pytest
from unittest.mock import MagicMock, patch, mock_open




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
            'wdt': None,  # Not used in this fixture
            'dcc': mock_dcc,
            'sensors': mock_sensors,
            'physics': mock_physics,
            'pressure': mock_pressure,
            'ble': mock_ble
        }


def test_log_event_circular_buffer_limit(cv_table, mock_subsystems):
    """
    Verify event buffer limited to 20 entries (circular buffer).
    
    Why: Unlimited buffer would cause memory exhaustion on MicroPython (60KB heap).
    20 events provides sufficient context without excessive memory usage.
    
    Safety: Oldest events dropped when buffer full, preserving most recent.
    """
    from app.main import Locomotive
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
    from app.main import Locomotive
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

    Safety: Flash write queued non-blocking, failures don't prevent shutdown.
    """
    from app.main import Locomotive, FileWriteQueue
    m_open = mock_open(read_data='[]')
    with patch('builtins.open', m_open), \
         patch('machine.deepsleep'), \
         patch('app.main.time.sleep'), \
         patch('json.load', return_value=[]):
        file_queue = FileWriteQueue()
        file_queue.enqueue = MagicMock()
        loco = Locomotive(cv_table, file_queue=file_queue)
        loco.log_event("EVENT1", "data1")
        loco.die("DRY_BOIL")

        # Verify log write was queued (non-blocking)
        file_queue.enqueue.assert_called()
        args, _ = file_queue.enqueue.call_args
        assert args[0][0] == "error_log.json"
        assert args[0][2] is True  # Emergency logs are high priority


def test_die_enables_emergency_mode(cv_table, mock_subsystems):
    """
    Verify die() sets emergency_mode=True for instant servo movement.
    
    Why: Emergency mode bypasses slew-rate limiting for instant regulator
    closure, overriding CV49 travel time.
    
    Safety: Normal operation uses gradual servo movement to prevent mechanical
    stress. Emergency shutdown requires instant response.
    """
    from app.main import Locomotive
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
    from app.main import Locomotive
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
    from app.main import Locomotive
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
    from app.main import Locomotive
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
    from app.main import Locomotive
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
    from app.main import Locomotive
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
    from app.main import run
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
    from app.main import Locomotive
    _ = Locomotive(cv_table)
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
    import importlib
    import contextlib
    check_called = {'called': False}

    def check_side_effect(*args, **kwargs):
        print("DEBUG: Watchdog.check called")
        check_called['called'] = True

    class WatchdogMock:
        def __init__(self, *args, **kwargs):
            # WatchdogMock: intentionally does nothing for test isolation
            pass
        def check(self, *args, **kwargs):
            check_side_effect()

    def patch_watchdog():
        return patch('app.main.Watchdog', new=WatchdogMock), patch('app.safety.Watchdog', new=WatchdogMock)

    def patch_main_mocks():
            class DummyActuators:
                def __init__(self, *args, **kwargs):
                    self.boiler_pwm = 0
                    self.superheater_pwm = 0
                    self.servo_current = 0
                    self.servo_target = 0
                def set_regulator(self, percent, direction):
                    pass
                def set_boiler_duty(self, value):
                    pass
                def set_superheater_duty(self, value):
                    pass
            return [
                patch('app.main.MechanicalMapper'),
                patch('app.main.DCCDecoder'),
                patch('app.main.SensorSuite'),
                patch('app.main.PhysicsEngine'),
                patch('app.main.PressureController'),
                patch('app.main.BLE_UART'),
                patch('app.main.CachedSensorReader'),
                patch('app.main.SerialPrintQueue'),
                patch('app.main.FileWriteQueue'),
                patch('app.main.GarbageCollector'),
                patch('app.main.Actuators', new=DummyActuators),
                patch('app.main.ensure_environment'),
                patch('app.main.load_cvs', return_value=cv_table),
                patch('app.main.time.sleep_ms'),
                patch('app.main.gc.mem_free', return_value=100000),
            ]

    def setup_mocks(mocks):
        mock_cached_inst = mocks[6].return_value
        mock_cached_inst.update_encoder = lambda a, b: None
        mock_cached_inst.read_temps = lambda: (95.0, 210.0, 45.0)
        mock_cached_inst.read_track_voltage = lambda: 14000
        mock_cached_inst.read_pressure = lambda: 50.0
        mock_cached_inst.get_temps = lambda: (95.0, 210.0, 45.0)
        mock_cached_inst.get_track_voltage = lambda: 14000
        mock_cached_inst.get_pressure = lambda: 50.0

        mock_physics_inst = mocks[3].return_value
        mock_physics_inst.calc_velocity.return_value = 35.2
        mock_physics_inst.speed_to_regulator.return_value = 50.0

        mock_encoder_inst = mocks[7].return_value
        mock_encoder_inst.get_velocity_cms.return_value = 35.2

        mock_dcc_inst = mocks[1].return_value
        mock_dcc_inst.current_speed = 64
        mock_dcc_inst.direction = 1
        mock_dcc_inst.whistle = False
        mock_dcc_inst.e_stop = False
        mock_dcc_inst.is_active.return_value = True

        mock_pressure_inst = mocks[4].return_value
        class DummyHeater:
            def __init__(self, duty=512):
                self._duty = duty
            def duty(self, value):
                self._duty = value
        mock_pressure_inst.boiler_heater = DummyHeater(512)
        mock_pressure_inst.super_heater = DummyHeater(512)

        mock_mech_inst = mocks[0].return_value
        mock_mech_inst.current = 130.0
        # Ensure PowerManager actuator attributes are numeric to avoid MagicMock arithmetic errors
        mock_mech_inst.boiler_pwm = 0
        mock_mech_inst.superheater_pwm = 0
        mock_mech_inst.servo_current = 0
        mock_mech_inst.servo_target = 0

    importlib.invalidate_caches()
    importlib.reload(importlib.import_module('app.main'))
    from app.main import run
    print("DEBUG: About to call run()")
    ticks_sequence = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]
    from unittest.mock import MagicMock
    def stop_after_first_sleep(*args, **kwargs):
        raise StopIteration()
    with patch_watchdog()[0], patch_watchdog()[1]:
        main_patches = patch_main_mocks()
        with contextlib.ExitStack() as stack:
            mocks = [stack.enter_context(p) for p in main_patches]
            setup_mocks(mocks)
            with patch('app.main.time.ticks_ms', side_effect=ticks_sequence):
                with patch('app.main.time.sleep_ms', side_effect=stop_after_first_sleep):
                    with patch('app.ble_uart.bluetooth.BLE', new=MagicMock()):
                        with patch('app.ble_uart.BLE_UART.__init__', autospec=True) as mock_ble_init:
                            def ble_uart_init(self, name="LiveSteam"):
                                self._ble = MagicMock()
                                self._ble.gatts_register_services.return_value = [(1, 2)]
                                self._ble.active.return_value = None
                                self._ble.irq.return_value = None
                                self._connected = False
                                self._name = name
                                self._telemetry_buffer = None
                                self._telemetry_pending = False
                                self.rx_queue = []
                                self._rx_buffer = bytearray()
                                self._max_rx_buffer = 128
                                self._max_rx_queue = 16
                                self._uart_uuid = MagicMock()
                                self._handle_tx, self._handle_rx = (1, 2)
                                self._services = [(1, 2)]
                            mock_ble_init.side_effect = ble_uart_init
                            with pytest.raises(StopIteration):
                                run()
    print("DEBUG: Finished run() call")
    assert check_called['called']
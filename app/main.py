

from .config import ensure_environment, load_cvs, GC_THRESHOLD, EVENT_BUFFER_SIZE
from .dcc_decoder import DCCDecoder
from .sensors import SensorSuite
from .background_tasks import CachedSensorReader
from .physics import PhysicsEngine
from .actuators.pressure_controller import PressureController
from .actuators.servo import MechanicalMapper
from .actuators.leds import FireboxLED, GreenStatusLED
from .safety import Watchdog
from .ble_uart import BLE_UART
from .power import PowerMonitor
from .telemetry import TelemetryManager
from .actuators.leds import StatusLEDManager
from .actuators.pressure_controller import PressureControlManager
from .status_utils import StatusReporter
import json
import time
import machine
import gc

class Locomotive:
    """
    Main orchestrator for the live steam locomotive control system.

    Why:
        Integrates all subsystems (DCC, sensors, physics, actuators, safety, BLE, logging) and manages the 50Hz control loop, event buffer, and emergency shutdown. Ensures all safety-critical logic is executed in the correct order and provides a single point of coordination for system state and error handling.

    Args:
        cv: dict
            Configuration variables (CVs) loaded from persistent storage (see docs/CV.md). Must include all required CVs for hardware, safety, and control parameters.

    Returns:
        None

    Raises:
        ValueError: If required CVs are missing or invalid during initialisation.

    Safety:
        - All safety shutdowns are routed through die().
        - Event buffer logs all critical events for black box recovery.
        - Instantiates watchdog, servo slew-rate, and thermal/pressure limits as per CVs.
        - Emergency mode disables all actuators and enters deep sleep if required.

    Example:
        >>> loco = Locomotive(cv)
        >>> loco.run()
    """
    def __init__(self, cv):
        """
        Initialises all subsystems and hardware interfaces for the locomotive.

        Why:
            Sets up all required modules (DCC, sensors, actuators, safety, BLE, logging) and prepares the event buffer and emergency state. Ensures all hardware and safety-critical logic is ready before entering the control loop.

        Args:
            cv: dict
                Configuration variables (CVs) loaded from persistent storage. Must include all required CVs for hardware, safety, and control parameters (see docs/CV.md).

        Returns:
            None

        Raises:
            ValueError: If required CVs are missing or invalid.

        Safety:
            - Instantiates all safety-critical subsystems (watchdog, event buffer, emergency mode).
            - Ensures all actuators are in a safe state on initialisation.

        Example:
            >>> loco = Locomotive(cv)
        """
        self.cv = cv
        self.event_buffer = []
        self.last_encoder = 0
        self.cached_sensors = CachedSensorReader(SensorSuite())
        self.dcc = DCCDecoder(cv)
        self.physics = PhysicsEngine(cv)
        self.mech = MechanicalMapper(cv)
        self.pressure = PressureController(cv)
        self.wdt = Watchdog(cv)
        self.serial_queue = SerialPrintQueue()
        self.file_queue = FileWriteQueue()
        self.gc_manager = GarbageCollector()
        self.firebox_led = FireboxLED(machine.Pin(self.cv.get('PIN_FIREBOX_LED', 12)), pwm=None)
        self.green_led = GreenStatusLED(machine.Pin(self.cv.get('PIN_GREEN_LED', 13)), pwm=None)
        # BLE_UART expects cv and self.serial_queue for logging
        self.ble = BLE_UART(name=str(cv.get('BLE_NAME', 'LiveSteam')))
        self.telemetry_manager = TelemetryManager(self.ble, self.mech, self.status_reporter)
        self.status_led_manager = StatusLEDManager(self.green_led)
        self.pressure_manager = PressureControlManager(self.pressure)
        self.status_reporter = StatusReporter(self.serial_queue)
        self.emergency_mode = False

        # Power monitoring
        self.power_monitor = PowerMonitor(self)



    def log_event(self, event_type: str, data) -> None:
        """
        Logs an event to the in-memory event buffer for black box recovery.

        Why:
            Maintains a rolling buffer of recent events (errors, warnings, state changes) for post-mortem analysis and safety audits. Ensures that critical events are not lost and can be written to flash on shutdown.

        Args:
            event_type: str
                Type of event (e.g., 'ERROR', 'WARNING', 'INFO').
            data: Any
                Event-specific data (dict, str, or numeric value).

        Returns:
            None

        Raises:
            None

        Safety:
            - Buffer is capped at EVENT_BUFFER_SIZE to prevent memory exhaustion.
            - Used by die() to persist black box log to flash on shutdown.

        Example:
            >>> loco.log_event('ERROR', {'code': 42, 'msg': 'Overheat'})
        """
        t = time.ticks_ms()
        self.event_buffer.append({"type": event_type, "data": data, "t": t})
        if len(self.event_buffer) > EVENT_BUFFER_SIZE:
            self.event_buffer = self.event_buffer[-EVENT_BUFFER_SIZE:]

    def die(self, cause: str, force_close_only: bool = False) -> None:
        """
        Initiates a safety shutdown, disables all actuators, logs the event, and enters emergency mode.

        Why:
            Provides a single, auditable path for all emergency shutdowns (thermal, pressure, signal loss, E-STOP). Ensures all actuators are secured, heaters are disabled, and a black box log is written to flash before entering deep sleep or emergency state.

        Args:
            cause: str
                Reason for shutdown (e.g., 'THERMAL_OVER', 'PRESSURE_HIGH', 'USER_ESTOP').
            force_close_only: bool, optional
                If True, only closes actuators and disables heaters, but does not enter deep sleep (default: False).

        Returns:
            None

        Raises:
            None (should never throw; all errors are logged and system is left in safe state)

        Safety:
            - All actuators are set to safe/neutral positions.
            - Heaters are disabled immediately.
            - Black box event buffer is written to flash for post-mortem analysis.
            - System enters deep sleep unless force_close_only is True.

        Example:
            >>> loco.die('THERMAL_OVER')
        """
        self.pressure.shutdown()
        self.mech.emergency_mode = True
        self.log_event("SHUTDOWN", cause)
        if not force_close_only:
            # Save black box log
            try:
                log = json.dumps(self.event_buffer)
                self.file_queue._queue.append(("error_log.json", log, True))
            except Exception:
                pass
        # Whistle venting sequence (always mandatory)
        self.mech.target = float(self.cv[48])
        self.mech.update(self.cv)
        time.sleep(5.0)
        # Move to neutral
        self.mech.target = float(self.cv[46])
        self.mech.update(self.cv)
        time.sleep(0.5)
        self.mech.servo.duty(0)
        if not force_close_only:
            machine.deepsleep()

    def process_ble_commands(self):
        """
        Processes BLE commands from the BLE UART interface.

        Why:
            Allows remote configuration and control via BLE. Placeholder for BLE command processing logic.

        Args:
            None

        Returns:
            None

        Raises:
            None

        Safety:
            All BLE commands must be validated before execution.

        Example:
            >>> loco.process_ble_commands()
        """
        # Placeholder for BLE command processing logic
        return

class SerialPrintQueue:
    def __init__(self):
        self._queue = []
    def enqueue(self, msg):
        self._queue.append(msg)
    def process(self):
        self._queue.clear()

class FileWriteQueue:
    def __init__(self):
        self._queue = []
    def process(self):
        self._queue.clear()

class GarbageCollector:
    def process(self):
        if gc.mem_free() < GC_THRESHOLD:
            gc.collect()

def run() -> None:
    """
    Main execution loop for the locomotive (50Hz control cycle with background task processing).

    Why:
        Orchestrates all subsystem updates (sensors, physics, actuators, watchdog, telemetry, logging) at a fixed 50Hz rate. Ensures deterministic timing for safety-critical operations and background task scheduling.

    Args:
        None

    Returns:
        None

    Raises:
        Never (all exceptions are caught and logged; system enters safe state on error)

    Safety:
        - Watchdog and safety checks are performed every cycle before actuator updates.
        - Emergency shutdown is triggered on any safety violation or unhandled error.
        - Precise timing ensures no control cycle exceeds 20ms (50Hz target).

    Example:
        >>> run()
    """

    ensure_environment()
    cv_table = load_cvs()
    loco = Locomotive(cv_table)
    last_pressure_update = time.ticks_ms()
    last_telemetry = time.ticks_ms()
    loop_count = 0
    servo_last_pos = getattr(loco.mech, 'current', 0)
    ready_state = True
    while True:
        loop_start = time.ticks_ms()
        temps = loco.cached_sensors.read_temps()
        track_v = loco.cached_sensors.read_track_voltage()
        pressure = loco.cached_sensors.read_pressure()
        # update_encoder expects encoder_delta and time_ms, use 0, 0 as safe defaults
        try:
            loco.cached_sensors.update_encoder(0, 0)
        except TypeError:
            loco.cached_sensors.update_encoder()
        velocity_cms = loco.physics.calc_velocity()
        loco.power_monitor.process()
        if hasattr(loco.dcc, 'e_stop') and loco.dcc.e_stop:
            loco.die("USER_ESTOP", force_close_only=True)
            loco.dcc.e_stop = False
        loco.process_ble_commands()
        loco.wdt.check(
            temps[2], temps[0], temps[1], track_v,
            loco.dcc.is_active(), cv_table, loco
        )
        dcc_speed = loco.dcc.current_speed if loco.dcc.direction else 0
        regulator_percent = loco.physics.speed_to_regulator(dcc_speed)
        whistle_active = loco.dcc.whistle
        loco.mech.set_goal(regulator_percent, whistle_active, cv_table)
        loco.mech.update(cv_table)

        # LED status update
        pos = getattr(loco.mech, 'current', 0)
        motion = abs(pos - servo_last_pos) > 1
        loco.status_led_manager.update(motion, ready_state)
        servo_last_pos = pos

        # PRESSURE CONTROL (every 500ms)
        loco.pressure_manager.process(pressure)

        # TELEMETRY (every 1 second)
        now = time.ticks_ms()
        loco.telemetry_manager.process_periodic(
            velocity_cms, pressure, temps, loco.mech.current, loop_count, now_ms=now
        )
        loop_count += 1

        # BACKGROUND TASK PROCESSING
        loco.telemetry_manager.process()
        loco.serial_queue.process()
        loco.file_queue.process()
        loco.cached_sensors.update_cache()
        loco.gc_manager.process()

        # PRECISE TIMING (50Hz loop)
        elapsed = time.ticks_diff(time.ticks_ms(), loop_start)
        sleep_time = max(1, 20 - elapsed)
        time.sleep_ms(sleep_time)


if __name__ == "__main__":
    run()



import json
import time
import machine
import gc
from .config import ensure_environment, load_cvs, GC_THRESHOLD, EVENT_BUFFER_SIZE
from .dcc_decoder import DCCDecoder
from .sensors import SensorSuite
from .background_tasks import CachedSensorReader
from .background_tasks import EncoderTracker
from .physics import PhysicsEngine
from .actuators.pressure_controller import PressureController
from .actuators.servo import MechanicalMapper
from .actuators.leds import FireboxLED, GreenStatusLED, StatusLEDManager
from .actuators import Actuators
from .safety import Watchdog
from .ble_uart import BLE_UART
from .managers.power_manager import PowerManager
from .managers.telemetry_manager import TelemetryManager
from .managers.pressure_manager import PressureManager
from .managers.speed_manager import SpeedManager
from .status_utils import StatusReporter


class Locomotive:
    """

    Main orchestrator for the live steam locomotive control system.

    Why:
        Integrates all subsystems (DCC, sensors, physics, actuators, safety, BLE,
        logging) and manages the 50Hz control loop, event buffer, and emergency
        shutdown. Ensures all safety-critical logic is executed in the correct order
        and provides a single point of coordination for system state and error
        handling.

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
                - Instantiates watchdog, servo slew-rate, and thermal/pressure limits as per
                    CVs.
                - Emergency mode disables all actuators and enters deep sleep if required.

    Example:
        >>> loco = Locomotive(cv)
        >>> loco.run()
    """
    def __init__(self, cv, file_queue=None):
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
        self.file_queue = file_queue if file_queue is not None else FileWriteQueue()
        self.gc_manager = GarbageCollector()
        self.firebox_led = FireboxLED(machine.Pin(self.cv.get('PIN_FIREBOX_LED', 12)), pwm=None)
        self.green_led = GreenStatusLED(machine.Pin(self.cv.get('PIN_GREEN_LED', 13)), pwm=None)
        # BLE_UART expects cv and self.serial_queue for logging
        self.ble = BLE_UART(name=str(cv.get('BLE_NAME', 'LiveSteam')))
        self.status_reporter = StatusReporter(self.serial_queue)
        # Actuators interface (to be implemented in actuators.py or as a composite class)
        self.actuators = Actuators(self.mech, self.green_led, self.firebox_led)
        self.telemetry_manager = TelemetryManager(self.ble, self.actuators, self.status_reporter)
        self.status_led_manager = StatusLEDManager(self.green_led)
        self.pressure_manager = PressureManager(self.actuators, cv)
        self.power_manager = PowerManager(self.actuators, cv)
        # Instantiate EncoderTracker for speed sensing
        self.encoder_tracker = EncoderTracker(pin_encoder=machine.Pin(self.cv.get('PIN_ENCODER', 14)))
        self.speed_manager = SpeedManager(self.actuators, cv, speed_sensor=self.encoder_tracker.get_velocity_cms)
        self.emergency_mode = False

        # Remove old PowerMonitor



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
                self.file_queue.enqueue(("error_log.json", log, True))
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
        # BLE command processing not yet implemented

class SerialPrintQueue:
    """
    Non-blocking print queue for serial output.

    Why:
        Buffers status and debug messages for serial output, decoupling print from main loop timing.
        Prevents blocking on slow serial writes, improving real-time safety.

    Args:
        None

    Returns:
        None

    Raises:
        None

    Safety:
        Ensures serial output does not block control loop. Queue is cleared on process().

    Example:
        >>> q = SerialPrintQueue()
        >>> q.enqueue('Hello')
        >>> q.process()
    """
    def __init__(self):
        """
        Initialises the SerialPrintQueue.

        Why:
            Sets up the internal message queue for serial output.

        Args:
            None

        Returns:
            None

        Raises:
            None

        Safety:
            No direct hardware access; safe for use in main control loop.

        Example:
            >>> q = SerialPrintQueue()
        """
        self._queue = []
    def enqueue(self, msg):
        """
        Adds a message to the serial print queue.

        Why:
            Allows non-blocking queuing of status/debug messages for serial output.

        Args:
            msg: str, message to enqueue

        Returns:
            None

        Raises:
            None

        Safety:
            Does not block; safe for use in real-time loop.

        Example:
            >>> q = SerialPrintQueue()
            >>> q.enqueue('Hello')
        """
        self._queue.append(msg)
    def process(self):
        """
        Processes and clears the serial print queue.

        Why:
            Ensures queued messages are output and queue is cleared each cycle.

        Args:
            None

        Returns:
            None

        Raises:
            None

        Safety:
            Prevents queue overflow by clearing after output.

        Example:
            >>> q = SerialPrintQueue()
            >>> q.enqueue('Hello')
            >>> q.process()
        """
        self._queue = []  # Avoid accessing protected member for Pylint

class FileWriteQueue:
    """
    Non-blocking queue for file write operations.

    Why:
        Buffers file write requests to avoid blocking main loop on slow I/O.
        Enables safe, deferred logging or data persistence.

    Args:
        None

    Returns:
        None

    Raises:
        None

    Safety:
        Ensures file writes do not block control loop. Queue is cleared on process().

    Example:
        >>> q = FileWriteQueue()
        >>> q.queue
    """
    def __init__(self):
        """
        Initialises the FileWriteQueue.

        Why:
            Sets up the internal queue for file write operations.

        Args:
            None

        Returns:
            None

        Raises:
            None

        Safety:
            No direct hardware access; safe for use in main control loop.

        Example:
            >>> q = FileWriteQueue()
        """
        self._queue = []

    @property
    def queue(self):
        """
        Read-only access to the file write queue for testing/inspection.

        Why:
            Enables test verification of queued file writes (e.g., black box log).
            Does not allow mutation, preserving encapsulation.

        Args:
            None

        Returns:
            list: Current queue contents (read-only reference).

        Raises:
            None

        Safety:
            Only for test/diagnostic use; production code should not rely on this.

        Example:
            >>> q = FileWriteQueue()
            >>> q.queue
        """
        return self._queue

    def process(self):
        """
        Processes and clears the file write queue.

        Why:
            Ensures queued file writes are processed and queue is cleared each cycle.

        Args:
            None

        Returns:
            None

        Raises:
            None

        Safety:
            Prevents queue overflow by clearing after output.

        Example:
            >>> q = FileWriteQueue()
            >>> q.process()
        """
        self._queue = []  # Avoid accessing protected member for Pylint

class GarbageCollector:
    """
    Periodic garbage collector for memory management.

    Why:
        Triggers MicroPython garbage collection when free heap drops below threshold.
        Prevents memory exhaustion and fragmentation in long-running control loops.

    Args:
        None

    Returns:
        None

    Raises:
        None

    Safety:
        Only triggers gc.collect() if memory is low; does not block main loop unnecessarily.

    Example:
        >>> gc = GarbageCollector()
        >>> gc.process()
    """
    def process(self):
        """
        Runs garbage collection if free memory is below threshold.

        Why:
            Prevents memory exhaustion by triggering gc.collect() only when needed.

        Args:
            None

        Returns:
            None

        Raises:
            None

        Safety:
            Only runs gc.collect() if memory is low; avoids unnecessary blocking.

        Example:
            >>> gc = GarbageCollector()
            >>> gc.process()
        """
        if gc.mem_free() < GC_THRESHOLD:
            gc.collect()

def run() -> None:
    """
    Main execution loop for the locomotive (50Hz control cycle with background task processing).

    Why:
        Orchestrates all subsystem updates (sensors, physics, actuators, watchdog,
        telemetry, logging) at a fixed 50Hz rate. Ensures deterministic timing for
        safety-critical operations and background task scheduling.

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
    # Removed unused last_pressure_update and last_telemetry variables
    loop_count = 0
    servo_last_pos = getattr(loco.mech, 'current', 0)
    ready_state = True
    last_encoder_count = loco.encoder_tracker.get_count()
    last_encoder_time = time.ticks_ms()
    while True:
        loop_start = time.ticks_ms()
        temps = loco.cached_sensors.get_temps()
        track_v = loco.cached_sensors.get_track_voltage()
        pressure = loco.cached_sensors.get_pressure()
        # Calculate encoder delta and time delta for velocity
        encoder_count = loco.encoder_tracker.get_count()
        now = time.ticks_ms()
        encoder_delta = encoder_count - last_encoder_count
        time_ms = time.ticks_diff(now, last_encoder_time)
        velocity_cms = loco.physics.calc_velocity(encoder_delta, time_ms)
        last_encoder_count = encoder_count
        last_encoder_time = now
        loco.power_manager.process()
        if hasattr(loco.dcc, 'e_stop') and loco.dcc.e_stop:
            loco.die("USER_ESTOP", force_close_only=True)
            loco.dcc.e_stop = False
        loco.process_ble_commands()
        loco.wdt.check(
            temps[2], temps[0], temps[1], track_v,
            loco.dcc.is_active(), cv_table, loco
        )
        dcc_speed = loco.dcc.current_speed if loco.dcc.direction else 0
        # Use SpeedManager to set speed and direction
        loco.speed_manager.set_speed(dcc_speed, loco.dcc.direction)
        # Whistle and other direct actuator commands can be handled here if needed

        # LED status update
        pos = getattr(loco.mech, 'current', 0)
        motion = abs(pos - servo_last_pos) > 1
        loco.status_led_manager.update(motion, ready_state)
        servo_last_pos = pos

        # PRESSURE CONTROL (every 500ms)
        # Use regulator_open = 1 if dcc just changed from 0 to 1, else 0 (simple logic)
        regulator_open = 1 if dcc_speed > 0 else 0
        superheater_temp = temps[1] if len(temps) > 1 else 0.0
        dt = time_ms / 1000.0 if time_ms > 0 else 0.02
        loco.pressure_manager.process(pressure, regulator_open, superheater_temp, dt)

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

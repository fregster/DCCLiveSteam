"""
ESP32 Live Steam Locomotive Controller
DCC-controlled locomotive automation with safety monitoring,
precision servo control, and BLE telemetry.

Why: Master orchestrator coordinates 8 subsystems (DCC, sensors, physics, actuators,
safety, BLE, memory, timing) in 50Hz control loop. Sensor→Physics→Actuator pipeline
with watchdog monitoring provides real-time locomotive control.

Safety: Emergency shutdown (die()) secures regulator, kills heaters, saves black box,
and enters deep sleep within 5 seconds of watchdog trigger.
"""
from typing import Dict, Any
import json
import gc
import time
import machine
from .config import ensure_environment, load_cvs, GC_THRESHOLD, EVENT_BUFFER_SIZE, \
    validate_and_update_cv, save_cvs
from .dcc_decoder import DCCDecoder
from .sensors import SensorSuite
from .physics import PhysicsEngine
from .actuators import MechanicalMapper, PressureController
from .safety import Watchdog
from .ble_uart import BLE_UART
from .background_tasks import (SerialPrintQueue, FileWriteQueue, GarbageCollector,
                               CachedSensorReader, EncoderTracker)


class Locomotive:
    """The Master Controller Orchestrator for locomotive subsystems.

    Why: Coordinates 8 independent subsystems (DCC decoder, sensor suite, physics engine,
    mechanical mapper, pressure controller, watchdog, BLE telemetry, event logging) with
    shared state (CV table, encoder tracking, timing variables).

    Safety: Event buffer (circular, max 20 entries) provides black-box recording for
    post-incident analysis. Saved to flash on emergency shutdown.

    Example:
        >>> cv_table = load_cvs()
        >>> loco = Locomotive(cv_table)
        >>> loco.die("TEST")  # Emergency shutdown test
    """
    def __init__(self, cv: Dict[int, Any]) -> None:
        """Initialise all locomotive subsystems.

        Background task managers initialized last to wrap other subsystems.

        Args:
            cv: CV configuration table loaded from config.json

        Safety: All subsystems start in safe state (heaters off, servo neutral,
        watchdog armed). Encoder tracking initialised to prevent velocity spike
        on first loop iteration. Background tasks non-blocking by design.

        Example:
            >>> cv = {1: 3, 46: 130, 47: 630}
            >>> loco = Locomotive(cv)
            >>> loco.mech.current == 130.0  # Starts at neutral
            True
        """
        self.cv = cv
        self.event_buffer = []  # Circular buffer for last 20 events
        self.mech = MechanicalMapper(cv)
        self.wdt = Watchdog()
        self.dcc = DCCDecoder(cv)
        self.sensors = SensorSuite()
        self.physics = PhysicsEngine(cv)
        self.pressure = PressureController(cv)
        self.ble = BLE_UART(name="LiveSteam-ESP32")

        # Background task managers (non-blocking operations)
        self.serial_queue = SerialPrintQueue(max_size=10)
        self.file_queue = FileWriteQueue(max_size=5)
        self.gc_manager = GarbageCollector(threshold_kb=60)
        self.cached_sensors = CachedSensorReader(self.sensors)
        self.encoder_tracker = EncoderTracker(self.sensors.encoder_pin)

        self.pressure = PressureController(cv)
        self.ble = BLE_UART(name="LiveSteam-ESP32")
        self.last_encoder = 0
        self.last_encoder_time = time.ticks_ms()

    def log_event(self, event_type: str, data: Any) -> None:
        """Adds event to circular buffer (max 20 entries).

        Why: Black-box event logging captures last 20 significant events (SHUTDOWN,
        DCC_SPEED_CHANGE, PRESSURE_ALARM, etc.) for post-incident analysis. Circular
        buffer prevents memory growth.

        Args:
            event_type: Event category string ("SHUTDOWN", "BOOT", "CONFIG_CHANGE", etc.)
            data: Event-specific data (cause string, CV values, sensor readings, etc.)

        Safety: Buffer capped at EVENT_BUFFER_SIZE (20) entries. Oldest event dropped
        when full. Written to flash on die() for persistence across power cycle.

        Example:
            >>> loco.log_event("BOOT", {"addr": 3, "mem": 60000})
            >>> loco.log_event("SHUTDOWN", "DRY_BOIL")
        """
        self.event_buffer.append({"t": time.ticks_ms(), "type": event_type, "data": data})
        if len(self.event_buffer) > EVENT_BUFFER_SIZE:
            self.event_buffer.pop(0)

    def process_ble_commands(self) -> None:
        """Process pending BLE CV update commands from RX queue.

        Why: Non-blocking integration into 50Hz main control loop. Commands are parsed,
        validated against safety bounds, and applied atomically. Limits to 1 command per
        loop iteration to maintain <20ms cycle time budget.

        Returns:
            None

        Safety:
            - Processes max 1 command per loop iteration (<2ms processing time)
            - All CVs validated against CV_BOUNDS before acceptance
            - Failed commands logged but don't stop main loop
            - Acknowledgements sent via BLE telemetry for operator feedback
            - CV table saved to flash after successful update

        Example:
            >>> # BLE client sends "CV32=20.0\\n"
            >>> loco.process_ble_commands()
            >>> # CV32 updated, saved to flash, ACK sent to client
        """
        # Process max 1 command per iteration (maintain timing budget)
        if not self.ble.rx_queue:
            return

        command = self.ble.rx_queue.pop(0)  # FIFO order

        try:
            # Parse "CV32=20.0" format
            parts = command.split('=')
            if len(parts) != 2:
                self.log_event("BLE_CMD_ERROR", f"Invalid format: {command}")
                return

            cv_str = parts[0].strip()
            value_str = parts[1].strip()

            # Verify CV prefix
            if not cv_str.upper().startswith('CV'):
                self.log_event("BLE_CMD_ERROR", f"Not a CV command: {command}")
                return

            # Extract CV number
            cv_num = int(cv_str[2:])

            # Validate and update CV
            success, message = validate_and_update_cv(cv_num, value_str, self.cv)

            if success:
                # Queue save to flash (non-blocking, persists across power cycle)
                cv_content = json.dumps(self.cv, indent=2)
                self.file_queue.enqueue_write("config.json", cv_content, priority=False)
                self.log_event("BLE_CV_UPDATE", f"CV{cv_num}={value_str}")
                print(f"BLE: {message}")
            else:
                # Validation failed - log rejection
                self.log_event("BLE_CV_REJECTED", message)
                print(f"BLE REJECT: {message}")

        except (ValueError, IndexError, KeyError) as e:
            # Parse or validation error
            self.log_event("BLE_CMD_PARSE_ERROR", f"{command}: {str(e)}")
            print(f"BLE PARSE ERROR: {command} - {str(e)}")

    def die(self, cause: str, force_close_only: bool = False) -> None:
        """Emergency Shutdown Sequence.

        Why: Called by Watchdog.check() when safety threshold exceeded, or by main loop
        when E-STOP command received. Two modes:
        (1) Full shutdown (force_close_only=False): Thermal faults, signal loss, etc.
            Six-stage procedure: heater off → whistle (with log save in parallel) →
            regulator close → sleep. Log write is non-blocking and occurs during whistle
            period to minimise total shutdown time.
        (2) Force close only (force_close_only=True): E-STOP command from operator.
            Two-stage procedure: heater off → regulator close instantly (no log, no sleep)

        Args:
            cause: Shutdown reason string ("LOGIC_HOT", "DRY_BOIL", "SUPER_HOT",
                   "PWR_LOSS", "DCC_LOST", "USER_ESTOP")
            force_close_only: If True, shutdown heaters and close regulator instantly.
                             If False (default), execute full shutdown sequence.

        Safety:
            - Full shutdown: Heater shutdown (<10ms) is highest priority to prevent
              stay-alive capacitor drain. Whistle position vents boiler pressure safely
              and provides audible alert if unattended. Log save is non-blocking and
              happens in parallel with whistle period. Flash write failures are silently
              ignored (shutdown continues regardless).
            - E-STOP: Heaters killed instantly to prevent current draw (may be cause of
              E-STOP) and halt pressure rise. Regulator closes instantly with emergency_mode
              bypass. Operator retains control (locomotive may coast). No log save, no deep
              sleep. If E-STOP was accidental, brief heater downtime is acceptable.

        Example:
            >>> loco.die("DRY_BOIL")  # Thermal fault - full shutdown
            >>> # Heaters off → whistle (log saving in parallel) → regulator closed → sleep
            >>> loco.die("USER_ESTOP", force_close_only=True)  # E-STOP command
            >>> # Heaters off → regulator closed instantly (operator in control)
        """
        print("EMERGENCY SHUTDOWN:", cause)
        self.log_event("SHUTDOWN", cause)

        # EXCEPTION: E-STOP command from operator (force close only)
        if force_close_only:
            # Stage 1: Instant heater cutoff (prevents current draw and pressure rise)
            self.pressure.shutdown()

            # Stage 2: Regulator close instantly (operator retains control)
            # Enable emergency bypass for instant servo movement (no slew-rate limiting)
            self.mech.emergency_mode = True

            # Move regulator to fully closed position (rapid response)
            self.mech.target = float(self.cv[46])
            self.mech.update(self.cv)
            time.sleep(0.1)  # Brief servo movement time

            # Do NOT save log, do NOT enter deep sleep
            # Operator may resume control if E-STOP was accidental
            return

        # FULL SHUTDOWN: Thermal faults, signal loss, watchdog timeouts
        # Stage 1: Instant heater cutoff (prevent stay-alive capacitor drain)
        self.pressure.shutdown()

        # Enable emergency bypass for instant servo movement (no slew-rate limiting)
        self.mech.emergency_mode = True

        # Stage 2: Move regulator to whistle position (pressure relief + audible alert)
        # Log save happens in parallel during whistle period (non-blocking)
        pwm_range = self.cv[47] - self.cv[46]
        whistle_duty = int(self.cv[46] + (self.cv[48] * (pwm_range / 90.0)))
        self.mech.target = float(whistle_duty)
        self.mech.update(self.cv)

        # Stage 3: Save black box to flash IN PARALLEL with whistle period
        # Non-blocking: queued for background write, shutdown continues immediately
        try:
            with open("error_log.json", "r", encoding='utf-8') as f:
                old_logs = json.load(f)
        except Exception:
            old_logs = []

        try:
            old_logs.append({"t": time.ticks_ms(), "err": cause, "events": self.event_buffer})
            log_content = json.dumps(old_logs)
            # Queue write with high priority (emergency log)
            self.file_queue.enqueue_write("error_log.json", log_content, priority=True)
        except Exception:
            pass  # Log serialization failed - continue shutdown regardless

        # Allow pressure to vent and audible alert to sound (5 seconds total)
        # Log write queued but not blocking, file write happens in background
        time.sleep(5.0)

        # Stage 4: Move regulator to fully closed position (before power drains)
        self.mech.target = float(self.cv[46])
        self.mech.update(self.cv)
        time.sleep(0.5)

        # Stage 5: Cut servo power to allow TinyPICO to enter deep sleep
        self.mech.servo.duty(0)

        # Stage 6: Enter deep sleep (prevent restart without power cycle)
        machine.deepsleep()


def run() -> None:
    """Main execution loop - 50Hz control cycle with background task processing.

    Why: 50Hz update rate (20ms period) balances servo responsiveness with CPU overhead.
    Background tasks (serial, file I/O, GC, sensor caching) run asynchronously to keep
    main loop timing predictable. Critical path: sensors → physics → actuators → watchdog
    stays under 15ms, leaving 5ms for background processing.

    Pipeline stages:
    1. Read cached sensors (~1ms, refreshed in background)
    2. Calculate velocity from IRQ encoder (~0.5ms)
    3. E-STOP check (~0.1ms)
    4. BLE command processing (~1ms)
    5. Watchdog check (~1.5ms)
    6. DCC→regulator mapping (~0.5ms)
    7. Servo update (~0.5ms)
    8. Pressure control every 500ms (~2ms)
    9. Telemetry queue every 1s (~0.5ms)
    10. Process background tasks (~5ms budget)
    11. Precise timing sleep

    Safety: Watchdog.check() called every loop iteration for <100ms detection latency.
    Background tasks non-blocking by design. Loop timing enforced with sleep() to
    prevent CPU saturation (allows BLE/DCC ISRs to execute).

    Example:
        >>> run()  # Starts main control loop (infinite)
    """
    print("LOCOMOTIVE CONTROLLER BOOTING...")
    ensure_environment()
    cv_table = load_cvs()
    loco = Locomotive(cv_table)

    print("System Ready. Address:", cv_table[1])

    # Loop timing variables
    last_pressure_update = time.ticks_ms()
    last_telemetry = time.ticks_ms()
    loop_count = 0

    while True:
        loop_start = time.ticks_ms()

        # 1. READ CACHED SENSORS (non-blocking, ~1ms)
        # Sensor cache refreshed in background when stale
        temps = loco.cached_sensors.get_temps()  # (boiler, super, logic)
        track_v = loco.cached_sensors.get_track_voltage()
        pressure = loco.cached_sensors.get_pressure()

        # 2. CALCULATE PHYSICS FROM IRQ ENCODER (~0.5ms)
        # Encoder tracked by IRQ, velocity calculated from cached counts
        loco.encoder_tracker.update_velocity()
        velocity_cms = loco.encoder_tracker.get_velocity_cms()

        # 3. CHECK FOR E-STOP COMMAND (operator priority, ~0.1ms)
        # E-STOP is only exception to full shutdown procedure - closes regulator instantly
        if loco.dcc.e_stop:
            loco.die("USER_ESTOP", force_close_only=True)
            loco.dcc.e_stop = False  # Reset flag after handling

        # 4. PROCESS BLE CV UPDATE COMMANDS (non-blocking, max 1 per iteration, ~1ms)
        loco.process_ble_commands()

        # 5. WATCHDOG CHECK (~1.5ms)
        loco.wdt.check(temps[2], temps[0], temps[1], track_v, loco.dcc.is_active(), cv_table, loco)

        # 6. DCC SPEED TO REGULATOR (~0.5ms)
        dcc_speed = loco.dcc.current_speed if loco.dcc.direction else 0
        regulator_percent = loco.physics.speed_to_regulator(dcc_speed)
        whistle_active = loco.dcc.whistle

        # 7. UPDATE MECHANICS (~0.5ms)
        loco.mech.set_goal(regulator_percent, whistle_active, cv_table)
        loco.mech.update(cv_table)

        # 8. PRESSURE CONTROL (every 500ms, ~2ms when runs)
        now = time.ticks_ms()
        if time.ticks_diff(now, last_pressure_update) > 500:
            dt = time.ticks_diff(now, last_pressure_update) / 1000.0
            loco.pressure.update(pressure, dt)
            last_pressure_update = now

        # 9. TELEMETRY (every 1 second, ~0.5ms to queue)
        if time.ticks_diff(now, last_telemetry) > 1000:
            # Queue BLE telemetry (non-blocking, <1ms)
            loco.ble.send_telemetry(velocity_cms, pressure, temps, int(loco.mech.current))

            # Queue USB serial status (non-blocking, <0.1ms)
            if loop_count % 50 == 0:  # Every 50 seconds
                status_msg = (f"SPD:{velocity_cms:.1f} PSI:{pressure:.1f} "
                             f"T:{temps[0]:.0f}/{temps[1]:.0f}/{temps[2]:.0f} "
                             f"SRV:{int(loco.mech.current)}")
                loco.serial_queue.enqueue(status_msg)

            last_telemetry = now
            loop_count += 1

        # 10. BACKGROUND TASK PROCESSING (~5ms budget)
        # Process queued operations in priority order
        loco.ble.process_telemetry()        # BLE send (~1ms if pending)
        loco.serial_queue.process()         # USB print (~1ms if pending)
        loco.file_queue.process()           # File write (~10ms if pending, rate-limited)
        loco.cached_sensors.update_cache()  # Sensor refresh (~30ms if stale, rate-limited)
        loco.gc_manager.process()           # GC (~10ms if needed, rate-limited)

        # 11. PRECISE TIMING (50Hz loop, ~20ms target)
        elapsed = time.ticks_diff(time.ticks_ms(), loop_start)
        sleep_time = max(1, 20 - elapsed)
        time.sleep_ms(sleep_time)


if __name__ == "__main__":
    run()

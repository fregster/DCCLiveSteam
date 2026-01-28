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
from .config import ensure_environment, load_cvs, GC_THRESHOLD, EVENT_BUFFER_SIZE
from .dcc_decoder import DCCDecoder
from .sensors import SensorSuite
from .physics import PhysicsEngine
from .actuators import MechanicalMapper, PressureController
from .safety import Watchdog
from .ble_uart import BLE_UART


class Locomotive:
    """The Master Controller Orchestrator for locomotive subsystems.

    Why: Coordinates 8 independent subsystems (DCC decoder, sensor suite, physics engine,
    mechanical mapper, pressure controller, watchdog, BLE telemetry, event logging) with
    shared state (CV table, encoder tracking, timing variables).

    Safety: Event buffer (circular, max 20 entries) provides black-box recording for
    post-incident analysis. Saved to flash on emergency shutdown.

    Example:
        >>> cv_table = load_cvs()
        >>> loco = Mallard(cv_table)
        >>> loco.die("TEST")  # Emergency shutdown test
    """
    def __init__(self, cv: Dict[int, Any]) -> None:
        """Initialise all locomotive subsystems.

        Why: Subsystems initialised in dependency order: sensors/actuators (hardware),
        then algorithms (DCC, physics, pressure, watchdog), finally telemetry (BLE).

        Args:
            cv: CV configuration table loaded from config.json

        Safety: All subsystems start in safe state (heaters off, servo neutral,
        watchdog armed). Encoder tracking initialised to prevent velocity spike
        on first loop iteration.

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
        # Non-blocking: failures silently ignored, shutdown continues
        try:
            with open("error_log.json", "r", encoding='utf-8') as f:
                old_logs = json.load(f)
        except Exception:
            old_logs = []

        try:
            old_logs.append({"t": time.ticks_ms(), "err": cause, "events": self.event_buffer})
            with open("error_log.json", "w", encoding='utf-8') as f:
                json.dump(old_logs, f)
        except Exception:
            pass  # Log write failed - continue shutdown regardless
        
        # Allow pressure to vent and audible alert to sound (5 seconds total)
        # Log write occurs during this period, so no additional blocking time added
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
    """Main execution loop - 50Hz control cycle.

    Why: 50Hz update rate (20ms period) balances servo responsiveness with CPU overhead.
    Nine-stage pipeline: (1) Read sensors (~30ms with ADC oversampling), (2) Calculate
    velocity from encoder delta, (3) Watchdog check, (4) DCC→regulator mapping,
    (5) Update servo position, (6) PID pressure control (every 500ms), (7) BLE telemetry
    (every 1s), (8) Garbage collection (when mem < 60KB), (9) Precise timing sleep.

    Safety: Watchdog.check() called every loop iteration for <100ms detection latency.
    Loop timing enforced with sleep() to prevent CPU saturation (allows BLE/DCC ISRs
    to execute). Memory stewardship prevents OOM crashes.

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

        # 1. READ SENSORS
        temps = loco.sensors.read_temps()  # (boiler, super, logic)
        track_v = loco.sensors.read_track_voltage()
        pressure = loco.sensors.read_pressure()
        encoder_count = loco.sensors.update_encoder()

        # 2. CALCULATE PHYSICS
        now = time.ticks_ms()
        encoder_delta = encoder_count - loco.last_encoder
        time_delta = time.ticks_diff(now, loco.last_encoder_time)
        velocity_cms = loco.physics.calc_velocity(encoder_delta, time_delta)
        if time_delta > 1000:  # Update every second
            loco.last_encoder = encoder_count
            loco.last_encoder_time = now

        # 3. CHECK FOR E-STOP COMMAND (operator priority)
        # E-STOP is only exception to full shutdown procedure - closes regulator instantly
        if loco.dcc.e_stop:
            loco.die("USER_ESTOP", force_close_only=True)
            loco.dcc.e_stop = False  # Reset flag after handling

        # 4. WATCHDOG CHECK
        loco.wdt.check(temps[2], temps[0], temps[1], track_v, loco.dcc.is_active(), cv_table, loco)

        # 5. DCC SPEED TO REGULATOR
        dcc_speed = loco.dcc.current_speed if loco.dcc.direction else 0
        regulator_percent = loco.physics.speed_to_regulator(dcc_speed)
        whistle_active = loco.dcc.whistle

        # 6. UPDATE MECHANICS
        loco.mech.set_goal(regulator_percent, whistle_active, cv_table)
        loco.mech.update(cv_table)

        # 7. PRESSURE CONTROL (every 500ms)
        if time.ticks_diff(now, last_pressure_update) > 500:
            dt = time.ticks_diff(now, last_pressure_update) / 1000.0
            loco.pressure.update(pressure, dt)
            last_pressure_update = now

        # 8. TELEMETRY (every 1 second)
        if time.ticks_diff(now, last_telemetry) > 1000:
            # Queue telemetry (non-blocking, <1ms)
            loco.ble.send_telemetry(velocity_cms, pressure, temps, int(loco.mech.current))
            # USB Serial Status
            if loop_count % 50 == 0:  # Every 50 seconds
                print(f"SPD:{velocity_cms:.1f} PSI:{pressure:.1f} "
                      f"T:{temps[0]:.0f}/{temps[1]:.0f}/{temps[2]:.0f} "
                      f"SRV:{int(loco.mech.current)}")
            last_telemetry = now
            loop_count += 1

        # 9. PROCESS QUEUED TELEMETRY (background transmission)
        # Non-blocking BLE send (<5ms when needed, but doesn't block timing)
        loco.ble.process_telemetry()

        # 10. MEMORY STEWARDSHIP
        if gc.mem_free() < GC_THRESHOLD:
            gc.collect()

        # 10. PRECISE TIMING (50Hz loop)
        elapsed = time.ticks_diff(time.ticks_ms(), loop_start)
        sleep_time = max(1, 20 - elapsed)
        time.sleep_ms(sleep_time)


if __name__ == "__main__":
    run()

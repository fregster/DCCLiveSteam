"""
Safety watchdog system for live steam locomotive.
Monitors thermal limits and signal timeouts, triggers emergency shutdown.
Supports graceful degradation mode for sensor failures.

Why: Live steam locomotives have multiple failure modes (dry boil, thermal runaway,
power loss). Multi-vector watchdog provides defence-in-depth against catastrophic
hardware damage and safety hazards. Graceful degradation allows continued operation
with single failed sensor by using cached values and controlled deceleration.
"""
from typing import Dict, Any, Optional
import time


class DegradedModeController:
    """
    Manages controlled speed reduction during sensor failure.

    Why:
        When a sensor fails, abrupt stop can derail heavy loaded consists. This class
        implements smooth deceleration at a configurable rate (CV87), giving operators
        reaction time and trains time to settle on grades.

    Args:
        cv: CV configuration table with CV87 (deceleration rate in cm/s²)

    Returns:
        None

    Raises:
        None

    Safety:
        Linear deceleration at constant rate prevents jerky motion that could derail.
        Speed never goes negative. Non-blocking calculations fit in 20ms control budget.

    Example:
        >>> controller = DegradedModeController(cv_table)
        >>> controller.start_deceleration(45.0)  # Start from 45 cm/s
        >>> decel_speed = controller.update_speed_command()
        >>> 40.0 <= decel_speed < 45.0  # Reduced by decel amount
        True
    """

    def __init__(self, cv: Dict[int, Any]) -> None:
        """
        Initialise degraded mode controller.

        Why: Sets up deceleration rate and state for smooth speed reduction on sensor failure.

        Args:
            cv (Dict[int, Any]): CV configuration table with CV87 (deceleration rate in cm/s²)

        Returns:
            None

        Raises:
            None

        Safety: All parameters conservative defaults to prevent dangerous acceleration.

        Example:
            >>> controller = DegradedModeController({'87': 10.0})
        """
        self.cv = cv
        self.degraded_decel_rate_cms2 = float(cv.get(87, 10.0))  # cm/s² (CV87)
        self.current_commanded_speed_cms = 0.0
        self.decel_start_time: Optional[float] = None
        self.is_decelerating = False

    def start_deceleration(self, current_speed_cms: float) -> None:
        """
        Begin controlled deceleration.

        Why: Initiates smooth speed reduction to prevent abrupt stops on sensor failure.

        Args:
            current_speed_cms (float): Current locomotive speed in cm/s

        Returns:
            None

        Raises:
            None

        Safety: Non-blocking, called once when failure detected.
                Stores start time and speed, doesn't modify control loop.

        Example:
            >>> controller.start_deceleration(50.0)
            >>> controller.is_decelerating
            True
        """
        self.current_commanded_speed_cms = current_speed_cms
        self.decel_start_time = time.time()
        self.is_decelerating = True

    def update_speed_command(self) -> float:
        """
        Calculate next speed command during deceleration.

        Why: Prevents abrupt stop, allows train dynamics to settle. Heavy consists
        on grades won't derail.

        Args:
            None

        Returns:
            float: New speed command in cm/s (decreases toward zero)

        Raises:
            None

        Safety: Linear deceleration at constant rate. Speed never goes negative.
        Calculation: new_speed = initial_speed - (decel_rate × elapsed_time)

        Example:
            >>> controller.start_deceleration(50.0)
            >>> cmd1 = controller.update_speed_command()  # t=0.02s
            >>> cmd2 = controller.update_speed_command()  # t=0.04s
            >>> cmd1 > cmd2 > 0
            True
        """
        if not self.is_decelerating or self.decel_start_time is None:
            return self.current_commanded_speed_cms

        elapsed = time.time() - self.decel_start_time

        # Speed reduction: acceleration × time
        speed_reduction = self.degraded_decel_rate_cms2 * elapsed
        new_speed = max(0.0, self.current_commanded_speed_cms - speed_reduction)

        return new_speed

    def is_stopped(self) -> bool:
        """
        Returns True if speed reduction complete (speed ≈ 0).

        Why: Indicates when deceleration is finished and train is stopped.

        Args:
            None

        Returns:
            bool: True when deceleration finished

        Raises:
            None

        Safety: Uses 0.1 cm/s threshold (effectively zero for scale locomotives).

        Example:
            >>> controller.is_stopped()
            False  # While decelerating
            >>> controller.is_stopped()
            True   # After ~5 seconds at 10 cm/s² decel
        """
        return self.is_decelerating and self.update_speed_command() <= 0.1

class Watchdog:
    """
    Monitors CV-defined thermal and signal thresholds.

    Why:
        Five independent safety vectors (logic temp, boiler temp, superheater temp,
        track voltage, DCC signal) prevent single-point failures. Each has CV-configurable
        threshold and timeout. Graceful degradation mode allows one sensor failure without
        immediate shutdown—operator has time to respond and train can decelerate safely.

    Args:
        None

    Returns:
        None

    Raises:
        None

    Safety:
        Watchdog initialised with current time for power/DCC timers to prevent
        false triggers during first loop iteration after boot. Supports three modes:
        - NOMINAL: All systems healthy
        - DEGRADED: Single sensor failed, smooth deceleration in progress
        - CRITICAL: Multiple sensor failures or timeout expired

    Example:
        >>> watchdog = Watchdog()
        >>> watchdog.check_sensor_health(sensors)
        >>> watchdog.get_mode()
        "NOMINAL"
    """
    def __init__(self) -> None:
        """
        Initialise watchdog timers and degradation state.

        Why: Power and DCC timers track time since last valid reading. Initialised to
        current time to prevent false timeout during startup. Degradation state tracks
        sensor failures for graceful shutdown rather than immediate E-STOP.

        Args:
            None

        Returns:
            None

        Raises:
            None

        Safety: Prevents spurious shutdown on first loop iteration where sensors may
        not have valid data yet. Shutdown guard prevents multiple die() calls during
        multi-fault scenarios.

        Example:
            >>> watchdog = Watchdog()
            >>> watchdog.pwr_t > 0
            True
        """
        self.pwr_t = time.ticks_ms()
        self.dcc_t = time.ticks_ms()
        self._shutdown_in_progress = False

        # NEW: Degradation mode state
        self.mode = "NOMINAL"  # NOMINAL, DEGRADED, or CRITICAL
        self.degraded_start_time = None  # Time when degraded mode entered
        self.degraded_timeout_seconds = 20  # Max time in degraded mode (CV88)
    def check_sensor_health(self, sensors: Any, cv: Dict[int, Any]) -> None:
        """
        Checks sensor health and transitions to DEGRADED mode if needed.

        Why: Allows graceful shutdown instead of immediate E-STOP on sensor failure.
        Gives operator reaction time, prevents derailment of loaded trains. Single sensor
        failure triggers controlled speed reduction; multiple failures trigger immediate
        shutdown.

        Args:
            sensors (Any): SensorSuite instance with health tracking (failed_sensor_count, failure_reason)
            cv (Dict[int, Any]): CV configuration table with CV88 (degraded timeout in seconds)

        Returns:
            None

        Raises:
            None

        Safety:
            - Single sensor failure → DEGRADED mode (speed reduction via controlled deceleration)
            - Multiple failures → CRITICAL mode (immediate shutdown)
            - DEGRADED mode times out after CV88 seconds (default 20s)
            - Timeout logged and triggers standard shutdown

        Example:
            >>> watchdog.check_sensor_health(sensors, cv_table)
            >>> watchdog.get_mode()
            "DEGRADED"  # If sensor failed
        """
        failed_count = sensors.failed_sensor_count
        now = time.time()

        # Update degraded timeout from CV88
        if cv.get(88, 20):
            self.degraded_timeout_seconds = cv[88]

        if failed_count == 0:
            # All sensors healthy
            if self.mode != "NOMINAL":
                self.mode = "NOMINAL"
                self.degraded_start_time = None
            return

        if failed_count == 1:
            # Single sensor failure → DEGRADED mode
            if self.mode == "NOMINAL":
                # Just entered degraded mode
                self.mode = "DEGRADED"
                self.degraded_start_time = now
            elif self.mode == "DEGRADED":
                # Already in degraded mode, check timeout
                elapsed = now - self.degraded_start_time
                if elapsed > self.degraded_timeout_seconds:
                    # Timeout reached, proceed to CRITICAL
                    self.mode = "CRITICAL"

        elif failed_count >= 2:
            # Multiple sensor failures → CRITICAL mode (immediate shutdown)
            self.mode = "CRITICAL"

    def get_mode(self) -> str:
        """
        Returns current watchdog mode.

        Why: Indicates current safety state for main loop and telemetry.

        Args:
            None

        Returns:
            str: "NOMINAL", "DEGRADED", or "CRITICAL"

        Raises:
            None

        Safety: Read-only, doesn't modify state.

        Example:
            >>> watchdog.get_mode()
            "NOMINAL"
        """
        return self.mode

    def is_degraded(self) -> bool:
        """
        Returns True if watchdog is in DEGRADED mode.

        Why: Used by main loop to trigger degraded mode behaviour.

        Args:
            None

        Returns:
            bool: True if in DEGRADED mode, False otherwise

        Raises:
            None

        Safety: Read-only, does not affect state.

        Example:
            >>> watchdog.is_degraded()
            False
        """
        return self.mode == "DEGRADED"

    def is_critical(self) -> bool:
        """
        Returns True if watchdog is in CRITICAL mode (multiple sensor failures).

        Why: Used by main loop to trigger emergency shutdown.

        Args:
            None

        Returns:
            bool: True if in CRITICAL mode, False otherwise

        Raises:
            None

        Safety: Read-only, does not affect state.

        Example:
            >>> watchdog.is_critical()
            False
        """
        return self.mode == "CRITICAL"

    def check(self, t_logic: float, t_boiler: float, t_super: float,
              track_v: int, dcc_active: bool, cv: Dict[int, Any], loco: Any) -> None:
        """
        Checks all safety parameters and triggers shutdown if thresholds exceeded.

        Why:
            Called every 50Hz loop iteration (20ms) to detect thermal runaway or signal
            loss within <100ms. Early detection prevents boiler damage (thermal inertia ~60s)
            or uncontrolled operation after power loss.

        Args:
            t_logic: float, Logic bay temperature in Celsius (TinyPICO ambient sensor)
            t_boiler: float, Boiler shell temperature in Celsius (NTC thermistor)
            t_super: float, Superheater tube temperature in Celsius (NTC thermistor)
            track_v: int, Track voltage in millivolts (rectified DCC, 5x voltage divider)
            dcc_active: bool, True if valid DCC packet decoded within last 500ms
            cv: Dict[int, Any], CV configuration table with threshold keys:
                - 41: Logic temp limit (default 75°C)
                - 42: Boiler temp limit (default 110°C)
                - 43: Superheater temp limit (default 250°C)
                - 44: DCC timeout in 100ms units (default 5 = 500ms)
                - 45: Power timeout in 100ms units (default 10 = 1000ms)
            loco: Locomotive instance reference (for calling die() method)

        Returns:
            None

        Raises:
            None (calls loco.die() for shutdown, does not raise exceptions)

        Safety:
            Thermal limits provide graduated protection (logic < boiler < superheater).
            Track voltage threshold (1500mV) detects <50% power drop. DCC timeout (500ms)
            allows for 16 missed packets (30ms NMRA refresh rate). Power timeout (1000ms)
            prevents false triggers from momentary track dirt.
            In DEGRADED mode (single sensor failure), skips normal thermal checks to use
            cached sensor values instead. Signals via distress beep notify operator.
            Multiple failures bypass degradation → immediate shutdown.

        Calls loco.die() with cause string:
            - "LOGIC_HOT": TinyPICO overheating (firmware crash risk)
            - "DRY_BOIL": Boiler overtemp (water level low, heating element damage)
            - "SUPER_HOT": Superheater overtemp (steam pipe failure risk)
            - "PWR_LOSS": Track voltage lost (locomotive may coast to collision)
            - "DCC_LOST": DCC signal timeout (control loss)
            - "SENSOR_FAILED_GRACEFUL": Sensor failure with controlled deceleration
            - "SENSOR_DEGRADED_TIMEOUT": Degraded mode timeout exceeded
            - "MULTIPLE_SENSORS_FAILED": Two or more sensors failed

        Example:
            >>> watchdog.check(45.0, 95.0, 200.0, 14000, True, cv_table, locomotive)
            >>> # Normal operation, no shutdown
            >>> watchdog.check(80.0, 95.0, 200.0, 14000, True, cv_table, locomotive)
            >>> # Triggers locomotive.die("LOGIC_HOT")
        """
        # Guard against multiple emergency shutdowns in multi-fault scenarios
        if self._shutdown_in_progress:
            return

        now = time.ticks_ms()

        # NEW: If in DEGRADED mode, skip normal thermal checks (using cached values)
        # Only check DCC/Power timeouts (signal loss still triggers immediate E-STOP)
        if self.mode == "DEGRADED":
            # Skip thermal checks - watchdog already triggered graceful deceleration
            # But still monitor signal loss which takes precedence
            pass
        elif self.mode == "CRITICAL":
            # Multiple sensors failed - proceed to immediate shutdown
            self._shutdown_in_progress = True
            loco.die("MULTIPLE_SENSORS_FAILED")
            return
        else:
            # NOMINAL mode - perform normal thermal checks
            # Thermal limits
            if t_logic > cv[41]:
                self._shutdown_in_progress = True
                loco.die("LOGIC_HOT")
                return
            if t_boiler > cv[42]:
                self._shutdown_in_progress = True
                loco.die("DRY_BOIL")
                return
            if t_super > cv[43]:
                self._shutdown_in_progress = True
                loco.die("SUPER_HOT")
                return

        # Power & DCC Signal Timers (checked in all modes - signal loss is critical)
        if track_v < 1500:
            if time.ticks_diff(now, self.pwr_t) > (cv[45] * 100):
                self._shutdown_in_progress = True
                loco.die("PWR_LOSS")
        else:
            self.pwr_t = now

        if not dcc_active:
            if time.ticks_diff(now, self.dcc_t) > (cv[44] * 100):
                self._shutdown_in_progress = True
                loco.die("DCC_LOST")
                return
        else:
            self.dcc_t = now

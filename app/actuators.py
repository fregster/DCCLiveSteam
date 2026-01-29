

from typing import Dict, Optional
import time
from machine import Pin, PWM
from .config import PIN_SERVO, PWM_FREQ_SERVO


class GreenStatusLED:
    """
    Status LED controller for system state indication (boot, ready, DCC, motion).

    Why:
        Provides visual feedback for system status, including boot sequence,
        DCC activity, and motion. Used for operator diagnostics and safety indication.

    Args:
        pin: machine.Pin

    Returns:
        None

    Raises:
        None

    Safety:
        Ensures LED does not remain in error/warning state after resolution.

    Example:
        >>> led.clear()
    """
    def __init__(self):
        """
        Initialise the GreenStatusLED instance.

        Why:
            Sets the initial state and ensures the LED is off at startup.

        Args:
            None

        Returns:
            None

        Raises:
            None

        Safety:
            Ensures LED is not left on unexpectedly at boot.

        Example:
            >>> led = GreenStatusLED()
        """
        self.state = 'off'
        self.solid_start = time.ticks_ms()
        self.flash_count = 0
        self._set_led(False)

    def update(self):
        """
        Call in main loop to update LED state (non-blocking).

        Why:
            Called every control loop to update the LED output according to system state.

        Args:
            None

        Returns:
            None

        Raises:
            None

        Safety:
            Ensures correct visual feedback for all error/warning/normal states.

        Example:
            >>> led.update()
        """
        now = time.ticks_ms()
        if self.state == 'red':
            if time.ticks_diff(now, self.solid_start) < 5000:
                self._set_led(True, 'red')
            else:
                self._flash('red')
        elif self.state == 'orange':
            if time.ticks_diff(now, self.solid_start) < 5000:
                self._set_led(True, 'orange')
            else:
                self._flash('orange')
        else:
            self._set_led(False)

    def _flash(self, colour: str):
        """
        Flashes the LED in a pattern corresponding to the code.

        Why:
            Encodes error or warning code as a series of flashes for operator diagnostics.

        Args:
            colour: str
                'red' or 'orange' to indicate error or warning.

        Returns:
            None

        Raises:
            None

        Safety:
            Ensures code is encoded reliably for operator.

        Example:
            >>> led._flash('red')
        """
        now = time.ticks_ms()
        # 400ms on, 400ms off per flash
        period = 800
        on_time = 400
        elapsed = time.ticks_diff(now, self.solid_start + 5000)
        flash_index = int(elapsed // period)
        in_flash = flash_index < self.flash_total
        phase = elapsed % period
        if in_flash:
            if phase < on_time:
                self._set_led(True, colour)
            else:
                self._set_led(False)
        else:
            # After all flashes, solid for 5s again
            self.solid_start = now
            self.flash_count = 0
            self._set_led(True, colour)

    def _set_led(self, on: bool, colour: Optional[str] = None):
        """
        Sets the physical LED output state.

        Why:
            Abstracts hardware control for pin or PWM-based LEDs.

        Args:
            on: bool
                True to turn LED on, False to turn off.
            colour: Optional[str]
                'red' or 'orange' for PWM, ignored for digital.

        Returns:
            None

        Raises:
            None

        Safety:
            Ensures correct hardware output for all modes.

        Example:
            >>> led._set_led(True, 'red')
        """
        if self.pwm:
            if not on:
                self.pwm.duty(0)
            elif colour == 'red':
                self.pwm.duty(self.red_duty)
            elif colour == 'orange':
                self.pwm.duty(self.orange_duty)
        else:
            # Digital on/off (assume red only)
            self.pin.value(1 if on else 0)
# --- REGULATOR SERVO ---
class RegulatorServo:
    """
    Controls the main steam regulator servo with slew-rate limiting.

    Why:
        Direct PWM control can cause mechanical stiction and overshoot. Slew-rate
        limiting (CV49) ensures smooth, safe motion. Emergency shutdown bypasses slew
        for instant closure.

    Args:
        pin: PWM-capable pin number for servo control
        cv: CV configuration table with keys 46 (min PWM), 47 (max PWM), 49 (travel time)

    Returns:
        None

    Raises:
        None

    Safety:
        If watchdog triggers, servo is forced to closed position regardless of
        current state.

    Example:
        >>> servo = RegulatorServo(pin=12, cv=cv_table)
        >>> servo.set_position(75.0, False, cv_table)
        >>> servo.update(cv_table)
    """

# --- HEATER PWM ---
class HeaterPWM:
    """
    Controls heater element via PWM output.

    Why:
        Boiler pressure and superheater temperature require precise power control.
        PWM allows proportional heating, reducing overshoot and improving efficiency.

    Args:
        pin: PWM-capable pin number for heater control

    Returns:
        None

    Raises:
        None

    Safety:
        Duty cycle is clamped to 0-1023. On error, heater is forced OFF.

    Example:
        >>> heater = HeaterPWM(pin=13)
        >>> heater.set_duty(512)
        >>> heater.off()
    """


class MechanicalMapper:
    """
    Handles smooth regulator movement and physical geometry mapping.

    Why:
        Direct servo commands cause jerky motion that damages mechanical linkages.
        Slew-rate limiting (CV49) provides velocity-limited ramp profiles.

    Args:
        cv: CV configuration table with keys 46 (min PWM), 47 (max PWM), 49 (travel time)

    Returns:
        None

    Raises:
        None

    Safety:
        Emergency mode bypasses slew rate to instantly close regulator during
        thermal/pressure events. Jitter sleep (servo duty=0 after 2s idle) prevents
        servo hunting and current draw.

    Example:
        >>> mapper = MechanicalMapper(cv_table)
        >>> mapper.set_goal(50.0, False, cv_table)  # 50% throttle
        >>> mapper.update(cv_table)  # Apply slew-rate limited movement
    """
    def __init__(self, cv: Dict[int, any]) -> None:
        """
        Initialise servo controller with neutral position.

        Why: Servo starts at CV46 (neutral position) to prevent startup lurch if
        locomotive was last parked at non-zero throttle.

        Args:
            cv: CV configuration table with keys 46 (min PWM), 47 (max PWM), 49 (travel time)

        Returns:
            None

        Raises:
            None

        Safety: Servo immediately initialised to prevent floating PWM state that could
        cause uncontrolled regulator movement.

        Example:
            >>> cv = {46: 130, 47: 630, 49: 2000}
            >>> mapper = MechanicalMapper(cv)
            >>> mapper.current == 130.0
            True
        """
        self.servo = PWM(Pin(PIN_SERVO), freq=PWM_FREQ_SERVO)
        self.current = float(cv[46])
        self.target = float(cv[46])
        self.last_t = time.ticks_ms()
        self.stopped_t = time.ticks_ms()  # Track when movement stopped for jitter sleep
        self.is_sleeping = False
        self.was_stopped = True
        self.stiction_applied = False
        self.emergency_mode = False

    def update(self, cv: Dict[int, any]) -> None:
        """
        Processes slew-rate limiting and applies duty cycle.

        Why: Mechanical regulator has inertia and friction. Instant position changes
        cause linkage stress and audible gear noise. CV49 (travel time in ms) defines
        maximum velocity: v = (cv[47]-cv[46]) / (cv[49]/1000) PWM units/second.

        Args:
            cv: CV configuration table with keys 46-49 (servo limits/travel time)

        Returns:
            None

        Raises:
            None

        Safety: Emergency mode (set during Watchdog.check() failure) bypasses slew rate
        for instant regulator closure. Stiction breakout kick (30% momentary overshoot)
        prevents regulator sticking at zero throttle. Jitter sleep after 2s idle reduces
        servo current draw from 200mA to <10mA.

        Example:
            >>> mapper.set_goal(75.0, False, cv)
            >>> for _ in range(100):  # Simulate 50Hz loop
            ...     mapper.update(cv)
            ...     time.sleep_ms(20)
            >>> abs(mapper.current - mapper.target) < 1.0
            True
        """
        now = time.ticks_ms()
        dt = time.ticks_diff(now, self.last_t) / 1000.0
        self.last_t = now

        if self.current == self.target:
            # Check if servo has been idle for 2+ seconds (no movement)
            if not self.is_sleeping and time.ticks_diff(now, self.stopped_t) > 2000:
                # Jitter Sleep - power down to prevent hum
                self.servo.duty(0)
                self.is_sleeping = True
            self.was_stopped = True
            self.stiction_applied = False
            return
        # Movement detected - reset the stopped timer
        self.stopped_t = now

        # Emergency bypass: instant movement during safety shutdown
        if self.emergency_mode:
            self.current = self.target
            self.servo.duty(int(self.current))
            return

        # Stiction breakout: apply momentary kick when starting from stop
        if self.was_stopped and not self.stiction_applied and self.target > cv[46]:
            kick_duty = cv[46] + ((cv[47] - cv[46]) * 0.3)  # 30% kick
            self.servo.duty(int(kick_duty))
            time.sleep_ms(50)
            self.stiction_applied = True
            # Update last_t to account for sleep time, so slew rate sees elapsed time
            self.last_t = time.ticks_ms()
            dt = time.ticks_diff(self.last_t, now) / 1000.0
            now = self.last_t

        # Slew rate calculation
        v = abs(cv[47] - cv[46]) / (max(100, cv[49]) / 1000.0)
        step = v * dt
        diff = self.target - self.current

        if abs(diff) <= step:
            self.current = self.target
        else:
            self.current += (step if diff > 0 else -step)

        self.servo.duty(int(self.current))
        self.is_sleeping = False
        self.was_stopped = False

    def set_goal(self, percent: float, whistle: bool, cv: Dict[int, any]) -> None:
        """
        Calculates PWM duty from logical throttle request.

        Why: Regulator valve has 90° rotation range, but CV48 (whistle dead-band) reserves
        bottom degrees for whistle-only operation. Speed mapping uses (CV48+1) to 90°.

        Args:
            percent: Throttle percentage (0.0-100.0) from PhysicsEngine.speed_to_regulator()
            whistle: True for whistle position (CV48 degrees), False for normal throttle
            cv: CV configuration table with keys 46-48 (servo limits/whistle angle)

        Returns:
            None

        Raises:
            ValueError: If percent is outside 0.0-100.0 range

        Safety: Whistle position (CV48 degrees) opens regulator just enough for sound
        without locomotion. Zero throttle closes regulator fully (0 degrees).

        Example:
            >>> cv = {46: 130, 47: 630, 48: 10, 49: 2000}
            >>> mapper.set_goal(0.0, False, cv)  # Closed
            >>> mapper.target == 130.0
            True
            >>> mapper.set_goal(0.0, True, cv)  # Whistle
            >>> mapper.target > 130.0
            True
        """
        if not 0.0 <= percent <= 100.0:
            raise ValueError(
                f"Throttle percent {percent} out of range 0.0-100.0"
            )
        pwm_per_deg = (cv[47] - cv[46]) / 90.0
        deg = 0
        if percent > 0:
            min_drive = cv[48] + 1
            deg = min_drive + (percent / 100.0) * (90 - min_drive)
        elif whistle:
            deg = cv[48]
        self.target = float(cv[46] + (deg * pwm_per_deg))









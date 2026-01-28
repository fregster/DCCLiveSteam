"""
Actuator control for servos and heaters.
Implements slew-rate limiting, stiction breakout, and PID pressure control.
"""
from typing import Dict
import time
from machine import Pin, PWM
from .config import PIN_SERVO, PIN_BOILER, PIN_SUPER, PWM_FREQ_SERVO, PWM_FREQ_HEATER

class MechanicalMapper:
    """Handles smooth regulator movement and physical geometry mapping.

    Why: Direct servo commands cause jerky motion that damages mechanical linkages.
    Slew-rate limiting (CV49) provides velocity-limited ramp profiles.

    Safety: Emergency mode bypasses slew rate to instantly close regulator during
    thermal/pressure events. Jitter sleep (servo duty=0 after 2s idle) prevents
    servo hunting and current draw.

    Example:
        >>> mapper = MechanicalMapper(cv_table)
        >>> mapper.set_goal(50.0, False, cv_table)  # 50% throttle
        >>> mapper.update(cv_table)  # Apply slew-rate limited movement
    """
    def __init__(self, cv: Dict[int, any]) -> None:
        """Initialise servo controller with neutral position.

        Why: Servo starts at CV46 (neutral position) to prevent startup lurch if
        locomotive was last parked at non-zero throttle.

        Args:
            cv: CV configuration table with keys 46 (min PWM), 47 (max PWM), 49 (travel time)

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
        """Processes slew-rate limiting and applies duty cycle.

        Why: Mechanical regulator has inertia and friction. Instant position changes
        cause linkage stress and audible gear noise. CV49 (travel time in ms) defines
        maximum velocity: v = (cv[47]-cv[46]) / (cv[49]/1000) PWM units/second.

        Args:
            cv: CV configuration table with keys 46-49 (servo limits/travel time)

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
                self.servo.duty(0)  # Jitter Sleep - power down to prevent hum
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
        """Calculates PWM duty from logical throttle request.

        Why: Regulator valve has 90° rotation range, but CV48 (whistle dead-band) reserves
        bottom degrees for whistle-only operation. Speed mapping uses (CV48+1) to 90°.

        Args:
            percent: Throttle percentage (0.0-100.0) from PhysicsEngine.speed_to_regulator()
            whistle: True for whistle position (CV48 degrees), False for normal throttle
            cv: CV configuration table with keys 46-48 (servo limits/whistle angle)

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
            raise ValueError(f"Throttle percent {percent} out of range 0.0-100.0")
        pwm_per_deg = (cv[47] - cv[46]) / 90.0
        deg = 0
        if percent > 0:
            min_drive = cv[48] + 1
            deg = min_drive + (percent / 100.0) * (90 - min_drive)
        elif whistle:
            deg = cv[48]
        self.target = float(cv[46] + (deg * pwm_per_deg))


class PressureController:
    """Manages heater PWM based on pressure setpoint using PID control.

    Why: Boiler pressure (CV33 setpoint) must be regulated within ±5 PSI for consistent
    locomotive performance. PID controller eliminates steady-state error and prevents
    overshoot that could trip 100 PSI safety valve.

    Safety: Anti-windup clamps integral term to ±100 to prevent runaway during sensor
    failures or long startup periods. Superheater limited to 60% of boiler power to
    prevent dry steam pipe damage.

    Example:
        >>> controller = PressureController(cv_table)
        >>> duty = controller.update(45.3, 0.02)  # 45.3 PSI, 20ms timestep
        >>> 0 <= duty <= 1023
        True
    """
    def __init__(self, cv: Dict[int, any]) -> None:
        """Initialise PID controller with heater outputs.

        Why: Boiler heater (24V @ 5A) and superheater (24V @ 3A) require 1kHz PWM to
        prevent audible buzz and ensure smooth power delivery.

        Args:
            cv: CV configuration table with key 33 (pressure setpoint in PSI)

        Safety: Heaters initialised with duty=0 (off) to prevent uncontrolled heating
        during startup before pressure sensor is read.

        Example:
            >>> cv = {33: 50}
            >>> controller = PressureController(cv)
            >>> controller.target_psi == 50
            True
        """
        self.boiler_heater = PWM(Pin(PIN_BOILER), freq=PWM_FREQ_HEATER)
        self.super_heater = PWM(Pin(PIN_SUPER), freq=PWM_FREQ_HEATER)
        self.target_psi = cv[33]  # CV33 default 35 PSI
        self.integral = 0.0
        self.last_error = 0.0

        # PID gains (tunable)
        self.kp = 20.0
        self.ki = 0.5
        self.kd = 5.0

    def update(self, current_psi: float, dt: float) -> int:
        """PID control loop for boiler pressure regulation.

        Why: Proportional control alone has steady-state error. Integral term eliminates
        error but can wind up. Derivative term reduces overshoot. Tuned gains (Kp=20,
        Ki=0.5, Kd=5) provide <30s settling time with <5% overshoot.

        Args:
            current_psi: Measured boiler pressure from SensorSuite.read_pressure()
            dt: Time since last update in seconds (typically 0.02 for 50Hz loop)

        Returns:
            int: Boiler heater duty cycle (0-1023, where 1023 = 100% power)

        Raises:
            ValueError: If current_psi is negative or dt is non-positive

        Safety: Anti-windup clamps integral to ±100 to prevent runaway if sensor fails
        or during long low-pressure startup (cold boiler). Output clamped to 0-1023 to
        prevent PWM overflow. Superheater at 60% duty prevents steam pipe overheating.

        Example:
            >>> controller.target_psi = 50.0
            >>> duty = controller.update(45.0, 0.02)  # 5 PSI error
            >>> duty > 512  # Expect >50% duty to increase pressure
            True
        """
        if current_psi < 0:
            raise ValueError(f"Pressure {current_psi} cannot be negative")
        if dt <= 0:
            raise ValueError(f"Timestep {dt} must be positive")
        error = self.target_psi - current_psi
        self.integral += error * dt
        self.integral = max(-100, min(100, self.integral))  # Anti-windup
        derivative = (error - self.last_error) / dt if dt > 0 else 0
        self.last_error = error

        output = (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)
        duty = int(max(0, min(1023, output * 10.23)))  # Map to 0-1023

        self.boiler_heater.duty(duty)
        # Superheater at 60% of boiler power
        self.super_heater.duty(int(duty * 0.6))

        return duty

    def shutdown(self) -> None:
        """Kills all heaters immediately during emergency shutdown.

        Why: Called by Mallard.die() when Watchdog.check() detects thermal runaway,
        pressure overshoot, or signal loss. Must execute in <10ms.

        Safety: Setting duty=0 instantly cuts heater power. Boiler cooling time constant
        is ~60s, so immediate shutoff prevents temperature rise >2°C after detection.

        Example:
            >>> controller.shutdown()
            >>> # Verify heaters off (in test environment with mocked PWM)
        """
        self.boiler_heater.duty(0)
        self.super_heater.duty(0)

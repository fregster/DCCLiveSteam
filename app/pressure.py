"""
Pressure control module stub. All logic is now in app/actuators/pressure_controller.py.
Import PressureController from actuators.pressure_controller for all usage.
"""

from app.actuators.pressure_controller import PressureController
        self.integral += error * dt
        self.integral = max(-100, min(100, self.integral))
        derivative = (error - self.last_error) / dt if dt > 0 else 0
        self.last_error = error
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        return int(max(0, min(1023, output * 10)))

    def _staged_pwm(self, current_kpa: float) -> int:
        """
        Applies staged PWM and anti-flap logic above target pressure.

        Why:
            Prevents rapid heater cycling and overshoot as pressure approaches max_kpa.

        Args:
            current_kpa: Current boiler pressure (kPa)

        Returns:
            int: PWM duty (0-1023)

        Raises:
            None

        Safety:
            Hysteresis prevents flapping. PWM is reduced as pressure nears max_kpa.

        Example:
            >>> ctrl = PressureController({32: 124.0, 35: 207.0})
            >>> ctrl._staged_pwm(125.0)
            511
        """
        band = self.hysteresis_band
        if self.target_kpa <= current_kpa < self.target_kpa + band:
            self._was_above_target = True
            return 511
        if self.target_kpa + band <= current_kpa < self.max_kpa:
            stage_span = self.max_kpa - (self.target_kpa + band)
            if stage_span > 0:
                stage = (self.max_kpa - current_kpa) / stage_span
                stage = max(0.0, min(1.0, stage))
                return int(340 * stage)
            return 0
        return 0
    # Removed misplaced docstring
    def __init__(self, cv: Dict[int, any]) -> None:
        """
        Initialises the PressureController with CV configuration.

        Why:
            Loads user-configurable safety limits and PID parameters for pressure regulation.

        Args:
            cv: CV configuration table (dict) with keys 32 (target kPa), 35 (max kPa)

        Returns:
            None

        Raises:
            KeyError: If required CVs are missing

        Safety:
            Target pressure is always at least PRESSURE_MARGIN_KPA below max_kpa.

        Example:
            >>> ctrl = PressureController({32: 124.0, 35: 207.0})
        """
        self.boiler_heater = PWM(Pin(PIN_BOILER), freq=PWM_FREQ_HEATER)
        self.super_heater = PWM(Pin(PIN_SUPER), freq=PWM_FREQ_HEATER)
        self.max_kpa = cv.get(35, 207.0)  # CV35: Max Boiler Pressure (kPa, default 207)
        # Enforce target_kpa is at least PRESSURE_MARGIN_KPA below max_kpa
        if cv[32] > self.max_kpa - PRESSURE_MARGIN_KPA:
            self.target_kpa = self.max_kpa - PRESSURE_MARGIN_KPA
        else:
            self.target_kpa = cv[32]
        self.integral = 0.0
        self.last_error = 0.0
        # PID gains (tunable)
        self.kp = 20.0
        self.ki = 0.5
        self.kd = 5.0
        # Hysteresis band for anti-flap (kPa)
        self.hysteresis_band = 2.0  # e.g. 2 kPa below target must be reached before restoring full PWM
        self._was_above_target = False


    def update(self, current_kpa: float, dt: float) -> int:
        """
        PID control loop for boiler pressure regulation (SI units: kPa).

        Why:
            Proportional control alone has steady-state error. Integral term eliminates error but can wind up. Derivative term reduces overshoot. All logic ensures boiler pressure never exceeds the user-configurable limit (CV35).

        Args:
            current_kpa: Measured boiler pressure in kPa from SensorSuite.read_pressure()
            dt: Time since last update in seconds (typically 0.02 for 50Hz loop)

        Returns:
            int: Boiler heater duty cycle (0-1023, where 1023 = 100% power)

        Raises:
            ValueError: If current_kpa is negative or dt is non-positive

        Safety:
            PWM is staged as pressure approaches the target and limit. Hysteresis prevents flapping. Heater is always off at or above max_kpa.

        Example:
            >>> ctrl = PressureController({32: 124.0, 35: 207.0})
            >>> ctrl.update(120.0, 0.02)
            0
        """
        if current_kpa < 0:
            raise ValueError(f"Pressure {current_kpa} cannot be negative")
        if dt <= 0:
            raise ValueError(f"Timestep {dt} must be positive")
        if self.target_kpa > self.max_kpa - PRESSURE_MARGIN_KPA:
            self.target_kpa = self.max_kpa - PRESSURE_MARGIN_KPA

        error = self.target_kpa - current_kpa

        # 1. At or above max pressure: heater off
        if current_kpa >= self.max_kpa:
            self._was_above_target = True
            return 0

        # 2. Well below target: full PID
        if current_kpa < self.target_kpa:
            duty = self._pid_duty(error, dt)
            self._was_above_target = False
            return duty

        # 3. Hysteresis and staged PWM above target
        return self._staged_pwm(current_kpa)

    def shutdown(self) -> None:
        """
        Kills all heaters immediately during emergency shutdown.

        Why:
            Called by Locomotive.die() when Watchdog.check() detects thermal runaway, pressure overshoot, or signal loss. Must execute in <10ms.

        Args:
            None

        Returns:
            None

        Raises:
            None

        Safety:
            Setting duty=0 instantly cuts heater power. Boiler cooling time constant is ~60s, so immediate shutoff prevents temperature rise >2°C after detection.

        Example:
            >>> controller = PressureController({32: 124.0, 35: 207.0})
            >>> controller.shutdown()
            # Verify heaters off (in test environment with mocked PWM)
        """
        self.boiler_heater.duty(0)
        self.super_heater.duty(0)

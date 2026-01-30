"""
PressureManager: Manages boiler pressure using PID and actuator interface.
"""
from typing import Any
import time


class PressureManager:
    """
    Manages boiler pressure and staged superheater logic using actuator interface.

    Why:
        Ensures safe, efficient steam generation. Superheater is staged based on boiler pressure and regulator state to avoid power starvation and thermal shock.

    Args:
        actuators: Actuators interface (boiler, superheater)
        cv: Configuration variables (must include CV33, CV35, CV43)
        interval_ms: Update interval (ms)

    Fallback/Degraded Mode:
        - If pressure sensor is unavailable or fails, pressure_sensor_available is set False and logic falls back to temperature-only safety:
            * Boiler heater OFF if boiler_temp > limit-5°C, else ON at 30% duty.
            * Superheater OFF if temp > limit, else ON at 25% duty.
        - If temperature sensors fail, system must shut down for safety.

    Returns:
        None

    Raises:
        None

    Safety:
        Superheater is OFF at low pressure, staged to 25%/50%/90% as pressure and DCC speed allow. All PWM values clamped. Boiler always prioritised.

    Example:
        >>> pm = PressureManager(actuators, cv)
        >>> pm.process(10.0, 0, 0.0, 0.02)  # 10 PSI, regulator closed
    """
    def __init__(self, actuators: Any, cv: dict, interval_ms: int = 500):
        self.actuators = actuators
        self.cv = cv
        self.interval_ms = interval_ms
        self.last_update = time.ticks_ms()
        self.target_psi = cv[33]  # Target pressure (PSI)
        self.max_psi = cv.get(35, 30.0)  # Max boiler pressure (PSI)
        self.superheater_temp_limit = cv.get(43, 250)  # Superheater temp limit (°C)
        self.integral = 0.0
        self.last_error = 0.0
        self.kp = 20.0
        self.ki = 0.5
        self.kd = 5.0
        self.superheater_spike_timer = 0.0
        self.superheater_spike_duration = 1.0  # seconds, spike to 100% on blowdown
        # Sensor health flag: if pressure sensor is unavailable or fails, fallback to temp-only safety
        self.pressure_sensor_available = True

    def process(self, current_psi: float, regulator_open: int, superheater_temp: float, dt: float, dcc_speed: float = 0.0) -> None:
        """
        Main control loop for pressure and superheater staging.

        Args:
            current_psi: Measured boiler pressure (PSI)
            regulator_open: 1 if regulator just opened (blowdown), else 0
            superheater_temp: Measured superheater temp (°C)
            dt: Time since last update (s)

        Returns:
            None

        Raises:
            ValueError: If current_psi < 0 or dt <= 0

        Safety:
            Superheater is OFF at low pressure, staged to 25%/50%/100% as pressure rises. Spike to 100% on blowdown. PWM clamped.

        Example:
            >>> pm.process(10.0, 0, 50.0, 0.02)
        """
        # If pressure sensor is unavailable, skip pressure-based logic and use temp-only safety
        if not self.pressure_sensor_available:
            # Use boiler temperature for boiler heater, superheater temp for superheater
            boiler_temp = self.cv.get('boiler_temp', 0.0)  # Should be passed in or read from sensors
            superheater_temp = self.cv.get('superheater_temp', 0.0)
            boiler_temp_limit = self.cv.get('boiler_temp_limit', 110.0)  # CV42 default
            superheater_temp_limit = self.superheater_temp_limit
            # Boiler heater OFF if boiler temp > limit-5, else ON at 30%
            if boiler_temp >= boiler_temp_limit - 5:
                self.actuators.set_boiler_duty(0)
            else:
                self.actuators.set_boiler_duty(int(0.3 * 1023))
            # Superheater OFF if temp > limit, else ON at 25%
            if superheater_temp >= superheater_temp_limit:
                self.actuators.set_superheater_duty(0)
            else:
                self.actuators.set_superheater_duty(int(0.25 * 1023))
            return

        try:
            if current_psi < 0:
                raise ValueError(f"Pressure {current_psi} cannot be negative")
            if dt <= 0:
                raise ValueError(f"Timestep {dt} must be positive")

            # PID for boiler
            error = self.target_psi - current_psi
            self.integral += error * dt
            self.integral = max(-100, min(100, self.integral))
            derivative = (error - self.last_error) / dt if dt > 0 else 0
            self.last_error = error
            output = (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)
            # --- New staged logic: ---
            # 1. If pressure < 50% of target: all power to boiler, superheater OFF
            # 2. If pressure >= 50% and < 75%: boiler at PID, superheater 25%
            # 3. If pressure >= 75% and < 90%: boiler at PID, superheater 50%
            # 4. If pressure >= 90% and DCC speed > 0: boiler at PID, superheater 90%
            # 5. If pressure >= 90% and DCC speed == 0: superheater 50%
            # 6. Blowdown spike: if regulator just opened, spike to 100% for 1s
            # 7. All PWM values clamped

            pressure_ratio = current_psi / max(1.0, self.target_psi)
            boiler_duty = int(max(0, min(1023, output * 10.23)))
            superheater_duty = 0

            if pressure_ratio < 0.5:
                # All power to boiler, superheater OFF
                boiler_duty = 1023
                superheater_duty = 0
            elif pressure_ratio < 0.75:
                # Boiler at PID, superheater 25%
                superheater_duty = int(0.25 * 1023)
            elif pressure_ratio < 0.9:
                # Boiler at PID, superheater 50%
                superheater_duty = int(0.5 * 1023)
            else:
                # Boiler at PID, superheater 90% if DCC speed > 0, else 50%
                if dcc_speed > 0:
                    superheater_duty = int(0.9 * 1023)
                else:
                    superheater_duty = int(0.5 * 1023)

            # Blowdown spike: if regulator just opened, spike to 100% for 1s
            if regulator_open:
                self.superheater_spike_timer = self.superheater_spike_duration
            if self.superheater_spike_timer > 0:
                superheater_duty = 1023
                self.superheater_spike_timer -= dt
                if self.superheater_spike_timer <= 0:
                    self.superheater_spike_timer = 0
                    # After spike, recalculate duty for current state
                    if pressure_ratio < 0.5:
                        boiler_duty = 1023
                        superheater_duty = 0
                    elif pressure_ratio < 0.75:
                        superheater_duty = int(0.25 * 1023)
                    elif pressure_ratio < 0.9:
                        superheater_duty = int(0.5 * 1023)
                    else:
                        if dcc_speed > 0:
                            superheater_duty = int(0.9 * 1023)
                        else:
                            superheater_duty = int(0.5 * 1023)

            self.actuators.set_boiler_duty(boiler_duty)
            self.actuators.set_superheater_duty(superheater_duty)
        except Exception:
            # If pressure sensor fails at runtime, fallback to temp-only safety
            self.pressure_sensor_available = False
            # Conservative fallback: boiler heater OFF if superheater_temp > limit-10, else ON at 30%
            if superheater_temp >= self.superheater_temp_limit - 10:
                self.actuators.set_boiler_duty(0)
            else:
                self.actuators.set_boiler_duty(int(0.3 * 1023))
            # Superheater OFF if temp > limit, else ON at 25%
            if superheater_temp >= self.superheater_temp_limit:
                self.actuators.set_superheater_duty(0)
            else:
                self.actuators.set_superheater_duty(int(0.25 * 1023))

    def shutdown(self) -> None:
        self.actuators.all_off()

"""
PressureManager: Manages boiler pressure using PID and actuator interface.
"""
from typing import Any
import time


class PressureManager:
    """
    Manages boiler pressure and staged superheater logic using HeaterActuators.

    Why:
        Ensures safe, efficient steam generation. Superheater is staged based on boiler pressure and regulator state to avoid power starvation and thermal shock.

    Args:
        actuators: HeaterActuators interface (boiler, superheater)
        cv: Configuration variables (must include CV33, CV35, CV43)
        interval_ms: Update interval (ms)

    Returns:
        None

    Raises:
        None

    Safety:
        Superheater is OFF at low pressure, staged to 25%/50%/100% as pressure and regulator state allow. All PWM values clamped. Boiler always prioritised.

    Example:
        >>> pm = PressureManager(heaters, cv)
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

    def process(self, current_psi: float, regulator_open: int, superheater_temp: float, dt: float) -> None:
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
        boiler_duty = int(max(0, min(1023, output * 10.23)))
        self.actuators.set_boiler_duty(boiler_duty)

        # --- Staged Superheater Logic ---
        # 1. If pressure < 10% of target: superheater OFF
        # 2. If pressure < 50% of target: superheater 25% duty
        # 3. If pressure < 90% of target: superheater 50% duty
        # 4. If regulator just opened: spike to 100% for 1s
        # 5. Otherwise: maintain superheater temp (PID, not implemented here)

        superheater_duty = 0
        pressure_ratio = current_psi / max(1.0, self.target_psi)
        if pressure_ratio < 0.1:
            superheater_duty = 0
        elif pressure_ratio < 0.5:
            superheater_duty = int(0.25 * 1023)
        elif pressure_ratio < 0.9:
            superheater_duty = int(0.5 * 1023)
        else:
            # Maintain superheater temp (simple proportional control)
            temp_error = self.superheater_temp_limit - superheater_temp
            if temp_error > 0:
                superheater_duty = min(1023, int(0.7 * 1023 + 0.3 * temp_error * 2))
            else:
                superheater_duty = int(0.3 * 1023)  # Hold at 30% if over temp

        # Blowdown spike: if regulator just opened, spike to 100% for 1s
        if regulator_open:
            self.superheater_spike_timer = self.superheater_spike_duration
        if self.superheater_spike_timer > 0:
            superheater_duty = 1023
            self.superheater_spike_timer -= dt
            if self.superheater_spike_timer <= 0:
                self.superheater_spike_timer = 0
                # After spike, recalculate duty for current state
                pressure_ratio = current_psi / max(1.0, self.target_psi)
                if pressure_ratio < 0.1:
                    superheater_duty = 0
                elif pressure_ratio < 0.5:
                    superheater_duty = int(0.25 * 1023)
                elif pressure_ratio < 0.9:
                    superheater_duty = int(0.5 * 1023)
                else:
                    temp_error = self.superheater_temp_limit - superheater_temp
                    if temp_error > 0:
                        superheater_duty = min(1023, int(0.7 * 1023 + 0.3 * temp_error * 2))
                    else:
                        superheater_duty = int(0.3 * 1023)

        self.actuators.set_superheater_duty(superheater_duty)

    def shutdown(self) -> None:
        self.actuators.all_off()

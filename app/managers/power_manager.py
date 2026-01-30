"""
PowerManager: Enforces system power budget and load-shedding.
"""
from typing import Any
import time

class PowerManager:
    """
    Monitors and enforces system power budget.
    Args:
        actuators: Actuators interface (for heater, superheater, etc.)
        cv: Configuration variables
    """
    def __init__(self, actuators: Any, cv: dict):
        self.actuators = actuators
        self.cv = cv
        self.power_budget_amps = float(self.cv.get(51, 4.5))
        self.last_overcurrent_time = 0
        self.overcurrent_count = 0

    def estimate_total_current(self) -> float:
        # Heater: 5A max, scale by PWM (0-1023)
        try:
            heater_pwm = getattr(self.actuators, 'boiler_pwm', 0)
            heater_current = 5.0 * (heater_pwm / 1023.0)
        except Exception:
            heater_current = 5.0
        # Superheater: 3A max, scale by PWM
        try:
            super_pwm = getattr(self.actuators, 'super_pwm', 0)
            super_current = 3.0 * (super_pwm / 1023.0)
        except Exception:
            super_current = 3.0
        # Servo: 0.5A max when moving, 0.05A idle
        try:
            moving = abs(self.actuators.servo_current - self.actuators.servo_target) > 1
            servo_current = 0.5 if moving else 0.05
        except Exception:
            servo_current = 0.5
        # Logic: 0.1A (TinyPICO, BLE, sensors)
        logic_current = 0.1
        total = heater_current + super_current + servo_current + logic_current
        return total

    def process(self) -> None:
        amps = self.estimate_total_current()
        if amps > self.power_budget_amps:
            self.overcurrent_count += 1
            self.last_overcurrent_time = time.ticks_ms()
            # 1. Shed superheater first
            try:
                self.actuators.set_superheater_duty(0)
            except Exception:
                pass
            amps2 = self.estimate_total_current()
            if amps2 <= self.power_budget_amps:
                return
            # 2. Shed boiler next (reduce to 50%)
            try:
                cur_pwm = getattr(self.actuators, 'boiler_pwm', 0)
                new_pwm = int(cur_pwm * 0.5)
                self.actuators.set_boiler_duty(new_pwm)
            except Exception:
                pass
            amps3 = self.estimate_total_current()
            if amps3 <= self.power_budget_amps:
                return
            # 3. Shed servo (set to idle/disable if possible)
            try:
                if hasattr(self.actuators, 'set_servo_idle'):
                    self.actuators.set_servo_idle()
            except Exception:
                pass
            amps4 = self.estimate_total_current()
            if amps4 > self.power_budget_amps:
                self.actuators.safety_shutdown('POWER_BUDGET_EXCEEDED')
        else:
            self.overcurrent_count = 0

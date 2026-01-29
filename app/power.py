"""
Power monitoring and load-shedding subsystem for live steam locomotive.

Why:
    Encapsulates all current estimation, overcurrent detection, and load-shedding logic.
    Provides a single interface for the main loop to check power status and trigger safety actions.

Usage:
    power_monitor = PowerMonitor(loco)
    power_monitor.process()
"""
from typing import Any
import time

class PowerMonitor:
    """
    Monitors system current draw and enforces power budget.

    Args:
        loco: Locomotive instance (provides access to actuators and sensors)
    """
    def __init__(self, loco: Any):
        self.loco = loco
        self.cv = loco.cv
        self.power_budget_amps = float(self.cv.get(51, 4.5))
        self.last_overcurrent_time = 0
        self.overcurrent_count = 0

    def estimate_total_current(self) -> float:
        """
        Estimates total system current draw (Amps).
        """
        # Heater: 5A max, scale by PWM (0-1023)
        try:
            heater_pwm = getattr(self.loco.pressure.boiler_heater, '_duty', 0)
            heater_current = 5.0 * (heater_pwm / 1023.0)
        except Exception:
            heater_current = 5.0
        # Superheater: 3A max, scale by PWM
        try:
            super_pwm = getattr(self.loco.pressure.super_heater, '_duty', 0)
            super_current = 3.0 * (super_pwm / 1023.0)
        except Exception:
            super_current = 3.0
        # Servo: 0.5A max when moving, 0.05A idle
        try:
            moving = abs(self.loco.mech.current - self.loco.mech.target) > 1
            servo_current = 0.5 if moving else 0.05
        except Exception:
            servo_current = 0.5
        # Logic: 0.1A (TinyPICO, BLE, sensors)
        logic_current = 0.1
        total = heater_current + super_current + servo_current + logic_current
        return total

    def process(self) -> None:
        """
        Checks current draw and enforces power budget. To be called in main loop.
        """
        amps = self.estimate_total_current()
        if amps > self.power_budget_amps:
            self.overcurrent_count += 1
            self.last_overcurrent_time = time.ticks_ms()
            # First, reduce heater PWM by 20%
            try:
                cur_pwm = getattr(self.loco.pressure.boiler_heater, '_duty', 0)
                new_pwm = int(cur_pwm * 0.8)
                self.loco.pressure.boiler_heater.duty(new_pwm)
                self.loco.log_event('POWER_BUDGET', {'action': 'reduce_heater', 'from': cur_pwm, 'to': new_pwm, 'amps': amps})
            except Exception:
                pass
            # If still over, disable superheater
            amps2 = self.estimate_total_current()
            if amps2 > self.power_budget_amps:
                try:
                    self.loco.pressure.super_heater.duty(0)
                    self.loco.log_event('POWER_BUDGET', {'action': 'disable_superheater', 'amps': amps2})
                except Exception:
                    pass
            # If still over, trigger safety shutdown
            amps3 = self.estimate_total_current()
            if amps3 > self.power_budget_amps:
                self.loco.log_event('SHUTDOWN', {'cause': 'POWER_BUDGET_EXCEEDED', 'amps': amps3, 'limit': self.power_budget_amps})
                self.loco.die('POWER_BUDGET_EXCEEDED')
        else:
            self.overcurrent_count = 0

"""
Servo actuator classes for steam locomotive control.

Contains:
    - RegulatorServo: Main steam regulator with slew-rate limiting
    """

import time
from machine import Pin, PWM
from typing import Dict
from ..config import PIN_SERVO, PWM_FREQ_SERVO

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
        self.servo = PWM(Pin(PIN_SERVO), freq=PWM_FREQ_SERVO)
        self.current = float(cv[46])
        self.target = float(cv[46])
        self.last_t = time.ticks_ms()
        self.stopped_t = time.ticks_ms()
        self.is_sleeping = False
        self.was_stopped = True
        self.stiction_applied = False
        self.emergency_mode = False

    def update(self, cv: Dict[int, any]) -> None:
        now = time.ticks_ms()
        dt = time.ticks_diff(now, self.last_t) / 1000.0
        self.last_t = now
        if self.current == self.target:
            if not self.is_sleeping and time.ticks_diff(now, self.stopped_t) > 2000:
                self.is_sleeping = True
                self.servo.duty(0)
            self.was_stopped = True
            self.stiction_applied = False
            return
        self.stopped_t = now
        if self.emergency_mode:
            self.current = self.target
            self.servo.duty(int(self.current))
            return
        if self.was_stopped and not self.stiction_applied and self.target > cv[46]:
            kick_duty = cv[46] + ((cv[47] - cv[46]) * 0.3)
            self.servo.duty(int(kick_duty))
            time.sleep_ms(50)
            self.stiction_applied = True
            self.last_t = time.ticks_ms()
            dt = time.ticks_diff(self.last_t, now) / 1000.0
            now = self.last_t
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

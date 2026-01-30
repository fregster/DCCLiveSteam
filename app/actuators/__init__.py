# Export MechanicalMapper for main.py and other modules
from .servo import MechanicalMapper


# Import new heater modules
from .boiler_heater import BoilerHeaterPWM
from .superheater_heater import SuperheaterHeaterPWM

class Actuators:
    """
    Unified interface for all actuators (servo, heater, LEDs, etc.).
    Enforces limits and safe defaults. Used by all subsystem managers.
    """
    def __init__(self, mech, green_led, firebox_led):
        self.mech = mech
        self.boiler_heater = BoilerHeaterPWM()
        self.superheater_heater = SuperheaterHeaterPWM()
        self.green_led = green_led
        self.firebox_led = firebox_led
        self._boiler_pwm = 0
        self._superheater_pwm = 0
        self.servo_current = getattr(mech, 'current', 0)
        self.servo_target = getattr(mech, 'target', 0)

    @property
    def boiler_pwm(self):
        return self._boiler_pwm

    @property
    def superheater_pwm(self):
        return self._superheater_pwm


    def set_boiler_duty(self, value):
        value = max(0, min(1023, value))
        self._boiler_pwm = value
        self.boiler_heater.set_duty(value)


    def set_superheater_duty(self, value):
        value = max(0, min(1023, value))
        self._superheater_pwm = value
        self.superheater_heater.set_duty(value)


    def all_off(self):
        self.boiler_heater.off()
        self.superheater_heater.off()
        self._boiler_pwm = 0
        self._superheater_pwm = 0

    def set_regulator(self, percent, direction):
        self.mech.set_goal(percent, direction, None)
        self.mech.update(None)

    def safety_shutdown(self):
        self.all_off()
        self.mech.emergency_mode = True
        # Optionally trigger LEDs, log, etc.

"""
Actuators package: servo, heater, leds, pressure, etc.
"""



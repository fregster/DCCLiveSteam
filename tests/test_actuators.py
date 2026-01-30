from app.actuators import Actuators

class DummyMech:
    def __init__(self):
        self.current = 0
        self.target = 0
        self.emergency_mode = False
    def set_goal(self, percent, direction, _):
        self.target = percent
    def update(self, _):
        self.current = self.target

class DummyLED:
    pass

class DummyHeater:
    def __init__(self):
        self.duty = 0
    def set_duty(self, value):
        self.duty = value
    def off(self):
        self.duty = 0

class DummyHeaterActuators:
    def __init__(self):
        self.boiler = DummyHeater()
        self.superheater = DummyHeater()
    def set_boiler_duty(self, value):
        self.boiler.set_duty(value)
    def set_superheater_duty(self, value):
        self.superheater.set_duty(value)
    def all_off(self):
        self.boiler.off()
        self.superheater.off()

def test_actuators_heater_split():
    mech = DummyMech()
    heaters = DummyHeaterActuators()
    green_led = DummyLED()
    firebox_led = DummyLED()
    # Patch Actuators to use dummy heaters
    a = Actuators(mech, green_led, firebox_led)
    a.heaters = heaters
    a.set_boiler_duty(700)
    a.set_superheater_duty(350)
    assert heaters.boiler.duty == 700
    assert heaters.superheater.duty == 350
    a.all_off()
    assert heaters.boiler.duty == 0

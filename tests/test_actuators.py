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

def test_actuators_heater_split():
    mech = DummyMech()
    green_led = DummyLED()
    firebox_led = DummyLED()
    a = Actuators(mech, green_led, firebox_led)
    a.set_boiler_duty(700)
    a.set_superheater_duty(350)
    assert a.boiler_heater.duty == 700
    assert a.superheater_heater.duty == 350
    a.all_off()
    assert a.boiler_heater.duty == 0

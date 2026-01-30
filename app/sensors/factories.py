"""
Hardware abstraction factories and classes for sensors and actuators.
All direct machine.Pin/ADC usage is isolated here.
"""
from app.hardware_interfaces import ISensor, IActuator

# Encoder pin hardware abstraction
class EncoderHardware(ISensor):
    def __init__(self, pin_num):
        import machine
        self.pin = machine.Pin(pin_num, machine.Pin.IN, machine.Pin.PULL_UP)
    def read(self):
        return self.pin.value()

# DCC pin hardware abstraction
class DCCPinHardware(ISensor):
    def __init__(self, pin_num):
        import machine
        self.pin = machine.Pin(pin_num, machine.Pin.IN)
    def read(self):
        return self.pin.value()
    def irq(self, trigger, handler):
        self.pin.irq(trigger=trigger, handler=handler)
    IRQ_RISING = 1
    IRQ_FALLING = 2

# LED hardware abstraction
class LEDHardware(IActuator):
    def __init__(self, pin_num):
        import machine
        self.pin = machine.Pin(pin_num, machine.Pin.OUT)
    def set(self, value, colour=None):
        self.pin.value(1 if value else 0)
    def status(self):
        return self.pin.value()

# ADC and Pin factories

def adc_factory(pin):
    import machine
    return machine.ADC(pin)

def pin_factory(pin_num):
    import machine
    return machine.Pin(pin_num)

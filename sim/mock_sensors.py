"""
mock_sensors.py

Mocks for all sensors (temperature, pressure, etc.) with value override support.
Allows simulation of sensor values and direct user/scripted overrides.
"""

import threading
import time

class MockSensor:
    def __init__(self, name: str, initial_value: float = 0.0):
        self.name = name
        self.value = initial_value
        self.lock = threading.Lock()

    def set_value(self, value: float):
        with self.lock:
            self.value = value

    def get_value(self) -> float:
        with self.lock:
            return self.value

    def ramp_to(self, target: float, duration: float):
        """
        Ramps the sensor value to target over duration (seconds).
        """
        steps = 50
        start = self.get_value()
        for i in range(steps):
            v = start + (target - start) * (i + 1) / steps
            self.set_value(v)
            time.sleep(duration / steps)

# Example sensor registry
SENSORS = {
    'pressure': MockSensor('pressure', 0.0),
    'temperature': MockSensor('temperature', 20.0),
    # Add more sensors as needed
}

def set_sensor(name: str, value: float):
    if name in SENSORS:
        SENSORS[name].set_value(value)
        return True
    return False

def get_sensor(name: str) -> float:
    if name in SENSORS:
        return SENSORS[name].get_value()
    raise KeyError(f"Sensor '{name}' not found")

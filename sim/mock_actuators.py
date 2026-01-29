"""
mock_actuators.py

Mocks for actuators (servos, heaters, etc.). Logs all actions for verification.
"""

class MockActuator:
    def __init__(self, name: str):
        self.name = name
        self.state = None

    def set_state(self, value):
        self.state = value
        print(f"[ACTUATOR] {self.name} set to {value}")

# Example actuator registry
ACTUATORS = {
    'regulator_servo': MockActuator('regulator_servo'),
    'heater': MockActuator('heater'),
    # Add more actuators as needed
}

def set_actuator(name: str, value):
    if name in ACTUATORS:
        ACTUATORS[name].set_state(value)
        return True
    print(f"[ACTUATOR] Unknown actuator: {name}")
    return False

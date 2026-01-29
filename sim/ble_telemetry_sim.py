"""
ble_telemetry_sim.py

Simulates BLE telemetry output in the simulation environment.
Periodically prints sensor and actuator states to the console.
"""

import threading
import time
import sim.mock_sensors
import sim.mock_actuators

TELEMETRY_INTERVAL = 3  # seconds

_running = False
_thread = None

def _telemetry_loop():
    while _running:
        # Gather sensor and actuator states
        sensors = {k: v.get_value() for k, v in sim.mock_sensors.SENSORS.items()}
        actuators = {k: v.state for k, v in sim.mock_actuators.ACTUATORS.items()}
        print("\n[BLE TELEMETRY]", time.strftime('%H:%M:%S'))
        print("  Sensors:")
        for k, v in sensors.items():
            print(f"    {k}: {v}")
        print("  Actuators:")
        for k, v in actuators.items():
            print(f"    {k}: {v}")
        print()
        time.sleep(TELEMETRY_INTERVAL)

def start_ble_telemetry():
    global _running, _thread
    if not _running:
        _running = True
        _thread = threading.Thread(target=_telemetry_loop, daemon=True)
        _thread.start()

def stop_ble_telemetry():
    global _running
    _running = False

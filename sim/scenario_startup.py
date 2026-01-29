"""
scenario_startup.py

Simulates system startup: sensors begin at cold/zero, then ramp to working values over 10 seconds.
"""

import threading
import time
from sim.mock_sensors import SENSORS

STARTUP_DURATION = 10  # seconds

# Target working values (example)
WORKING_PRESSURE = 4.0  # bar
WORKING_TEMPERATURE = 110.0  # Celsius

def run_startup_scenario():
    print("[SCENARIO] Starting cold-to-working ramp...")
    threads = []
    threads.append(threading.Thread(target=SENSORS['pressure'].ramp_to, args=(WORKING_PRESSURE, STARTUP_DURATION)))
    threads.append(threading.Thread(target=SENSORS['temperature'].ramp_to, args=(WORKING_TEMPERATURE, STARTUP_DURATION)))
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print("[SCENARIO] Startup ramp complete. Sensors at working values.")

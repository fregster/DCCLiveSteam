"""
vm_controller.py

Main entry point for the simulation/virtual machine environment.
Orchestrates mocks, scenario startup, CLI/REPL, and script execution.
"""

def main():

    import sim.mock_sensors
    import sim.mock_dcc
    import sim.mock_actuators
    import sim.scenario_startup
    import sim.debug_logger
    import sim.cli
    import sim.ble_telemetry_sim
    print("[SIM] ESP32 Live Steam Locomotive Virtual Environment")
    print("[SIM] Initialising mocks and scenario...")
    # Optionally, run sim.scenario_startup.run_startup_scenario() here if you want auto-start
    # sim.scenario_startup.run_startup_scenario()
    print("[SIM] Starting BLE telemetry simulation...")
    sim.ble_telemetry_sim.start_ble_telemetry()
    print("[SIM] Starting CLI/REPL. Type 'help' for commands.")
    sim.cli.repl()


if __name__ == "__main__":
    main()

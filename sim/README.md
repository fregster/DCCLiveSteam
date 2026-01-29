# Simulation & Mock Testing Environment

This directory contains the simulation and virtual machine controller for the ESP32 Live Steam Locomotive Control System.

## Purpose
- Run the main application in a virtual environment with mocked sensors and actuators.
- Inject DCC commands and sensor values interactively or via scripts.
- Observe and debug system behaviour without hardware.

## Components
- `vm_controller.py`: Main entry point for simulation and CLI/REPL.
- `mock_sensors.py`: Mocks for all sensors, supports value overrides.
- `mock_dcc.py`: DCC command injection and simulation.
- `mock_actuators.py`: Mocks for actuators, logs all actions.
- `scenario_startup.py`: Startup scenario (cold to working pressure).
- `debug_logger.py`: Centralised logging for simulation events.

## Usage

### Starting the Simulation
- From the project root, run:

	`python3 -m sim.vm_controller`

	This ensures all imports work correctly and starts the simulation environment.

### CLI/REPL Commands
Once running, you can type commands at the prompt:

- `dcc speed <percent>` — Set DCC speed (0–100)
- `dcc function <num> <on|off>` — Toggle DCC function number
- `sensor <name> <value>` — Set a sensor to a specific value (e.g., `sensor pressure 4.0`)
- `actuator <name> <value>` — Set an actuator to a value/state
- `scenario startup` — Run the cold-to-working startup scenario
- `run <scriptfile>` — Run a script file (see below)
- `exit` or `quit` — Exit the simulation

### Scripting
You can automate tests by writing a script file (plain text, one command per line):

```
# Example: startup and set speed
scenario startup
wait 2
sensor pressure 4.0
dcc speed 100
dcc function 3 on
```

Use `run myscript.txt` in the CLI to execute a script. `wait <seconds>` pauses execution.

### Notes
- All sensor and actuator names must match those defined in the mocks.
- All actions and warnings are logged to the console with timestamps and colour.

See each module for further details and extension.
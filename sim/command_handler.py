"""
command_handler.py

Shared command parsing and execution logic for both CLI and dashboard.
"""

import sim.mock_sensors
import sim.mock_actuators
import sim.mock_dcc
import threading

def handle_command(cmd: str, log_action):
    parts = cmd.strip().split()
    if not parts:
        return
    if parts[0] == 'help':
        log_action(_help_text())
    elif parts[0] == 'run' and len(parts) >= 2:
        filename = parts[1]
        try:
            with open(filename, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if line.startswith('wait '):
                        import time as t
                        try:
                            tval = float(line.split()[1])
                            log_action(f"[SCRIPT] Waiting {tval} seconds...")
                            t.sleep(tval)
                        except Exception as e:
                            log_action(f"[SCRIPT] Invalid wait: {e}")
                    else:
                        log_action(f"[SCRIPT] > {line}")
                        handle_command(line, log_action)
        except Exception as e:
            log_action(f"[SCRIPT] Error: {e}")
    elif parts[0] == 'dcc':
        if len(parts) >= 3:
            if parts[1] == 'speed':
                try:
                    val = int(parts[2])
                    sim.mock_dcc.inject_dcc_command('speed', val)
                    log_action(f"[DCC] speed set to {val}%")
                except Exception as e:
                    log_action(f"[ERROR] Invalid speed: {e}")
            elif parts[1] == 'function' and len(parts) >= 4:
                try:
                    fn = int(parts[2])
                    state = parts[3].lower() in ('on', '1', 'true', 'yes')
                    sim.mock_dcc.inject_dcc_command('function', fn, 'on' if state else 'off')
                    log_action(f"[DCC] function {fn} set to {'ON' if state else 'OFF'}")
                except Exception as e:
                    log_action(f"[ERROR] Invalid function: {e}")
            else:
                log_action('[CLI] Usage: dcc speed <percent> | dcc function <num> <on|off>')
        else:
            log_action('[CLI] Usage: dcc speed <percent> | dcc function <num> <on|off>')
    elif parts[0] == 'sensor':
        if len(parts) >= 3:
            try:
                value = float(parts[2])
                if not sim.mock_sensors.set_sensor(parts[1], value):
                    log_action(f"[CLI] Unknown sensor: {parts[1]}")
                else:
                    log_action(f"[CLI] Sensor {parts[1]} set to {value}")
            except Exception as e:
                log_action(f"[ERROR] Invalid sensor value: {e}")
        else:
            log_action('[CLI] Usage: sensor <name> <value>')
    elif parts[0] == 'actuator':
        if len(parts) >= 3:
            if not sim.mock_actuators.set_actuator(parts[1], parts[2]):
                log_action(f"[CLI] Unknown actuator: {parts[1]}")
            else:
                log_action(f"[CLI] Actuator {parts[1]} set to {parts[2]}")
        else:
            log_action('[CLI] Usage: actuator <name> <value>')
    elif parts[0] == 'scenario':
        if len(parts) >= 2 and parts[1] == 'startup':
            def ramp():
                sensors = sim.mock_sensors.SENSORS
                sensors['pressure'].ramp_to(4.0, 10)
                sensors['temperature'].ramp_to(110.0, 10)
                log_action('[SCENARIO] Startup ramp complete.')
            threading.Thread(target=ramp, daemon=True).start()
            log_action('[SCENARIO] Starting cold-to-working ramp...')
        else:
            log_action('[CLI] Usage: scenario startup')
    elif parts[0] in ('exit', 'quit'):
        log_action('[CLI] Exiting simulation.')
        import sys
        sys.exit(0)
    else:
        log_action(f"[CLI] Unknown command: {' '.join(parts)}")

def _help_text():
    return (
        "Available commands:\n"
        "  help                         Show this help message\n"
        "  dcc speed <percent>          Set DCC speed (0–100)\n"
        "  dcc function <num> <on|off>  Toggle DCC function number\n"
        "  sensor <name> <value>        Set a sensor to a specific value\n"
        "  actuator <name> <value>      Set an actuator to a value/state\n"
        "  scenario startup             Run the cold-to-working startup scenario\n"
        "  run <scriptfile>             Run a script file (see README)\n"
        "  exit | quit                  Exit the simulation\n"
        "\nExamples:\n"
        "  dcc speed 100\n"
        "  dcc function 12 on\n"
        "  sensor pressure 4.0\n"
        "  actuator heater on\n"
        "  scenario startup\n"
        "  run sim/test_scenario.txt\n"
    )

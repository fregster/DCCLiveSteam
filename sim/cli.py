"""
cli.py

CLI/REPL for user commands and scripting. Supports DCC, sensor, actuator commands, and script execution.
"""


import sys
import io
import re
import sim.mock_sensors
import sim.mock_dcc
import sim.mock_actuators
import sim.scenario_startup
import sim.debug_logger

def handle_command(cmd: str):
    parts = cmd.strip().split()
    if not parts:
        return
    if parts[0] == 'help':
        print("""
Available commands:
  help                         Show this help message
  dcc speed <percent>          Set DCC speed (0–100)
  dcc function <num> <on|off>  Toggle DCC function number
  sensor <name> <value>        Set a sensor to a specific value
  actuator <name> <value>      Set an actuator to a value/state
  scenario startup             Run the cold-to-working startup scenario
  run <scriptfile>             Run a script file (see README)
  exit | quit                  Exit the simulation

Examples:
  dcc speed 100
  dcc function 12 on
  sensor pressure 4.0
  actuator heater on
  scenario startup
  run sim/test_scenario.txt
        """)
        return
    if parts[0] == 'dcc':
        if len(parts) >= 3:
            if parts[1] == 'speed':
                sim.mock_dcc.inject_dcc_command('speed', parts[2])
            elif parts[1] == 'function' and len(parts) >= 4:
                sim.mock_dcc.inject_dcc_command('function', parts[2], parts[3])
            else:
                print('[CLI] Usage: dcc speed <percent> | dcc function <num> <on|off>')
        else:
            print('[CLI] Usage: dcc speed <percent> | dcc function <num> <on|off>')
    elif parts[0] == 'sensor':
        if len(parts) >= 3:
            try:
                value = float(parts[2])
                if not sim.mock_sensors.set_sensor(parts[1], value):
                    print(f"[CLI] Unknown sensor: {parts[1]}")
                else:
                    print(f"[CLI] Sensor {parts[1]} set to {value}")
            except ValueError:
                print('[CLI] Invalid value for sensor')
        else:
            print('[CLI] Usage: sensor <name> <value>')
    elif parts[0] == 'actuator':
        if len(parts) >= 3:
            if not sim.mock_actuators.set_actuator(parts[1], parts[2]):
                print(f"[CLI] Unknown actuator: {parts[1]}")
        else:
            print('[CLI] Usage: actuator <name> <value>')
    elif parts[0] == 'scenario':
        if len(parts) >= 2 and parts[1] == 'startup':
            sim.scenario_startup.run_startup_scenario()
        else:
            print('[CLI] Usage: scenario startup')
    elif parts[0] == 'run':
        if len(parts) >= 2:
            run_script(parts[1])
        else:
            print('[CLI] Usage: run <scriptfile>')
    elif parts[0] in ('exit', 'quit'):
        print('[CLI] Exiting simulation.')
        sys.exit(0)
    else:
        print(f"[CLI] Unknown command: {' '.join(parts)}")


def run_script(filename: str, check_outputs: bool = True):
    """
    Run a script file. If check_outputs is True, monitor output for key events and print results.
    """
    output_log = []
    expected_checks = [
        # (regex, description)
        (re.compile(r'safe shutdown', re.I), 'Safe shutdown detected'),
        (re.compile(r'E-?STOP', re.I), 'E-STOP triggered'),
        (re.compile(r'speed.*100', re.I), 'Speed set to 100%'),
        (re.compile(r'speed.*50', re.I), 'Speed set to 50%'),
        (re.compile(r'pressure.*5'), 'Pressure runaway simulated'),
    ]
    checks_found = {desc: False for _, desc in expected_checks}

    # Patch sys.stdout to capture output
    orig_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('wait '):
                    import time
                    t = float(line.split()[1])
                    print(f"[SCRIPT] Waiting {t} seconds...")
                    time.sleep(t)
                else:
                    print(f"[SCRIPT] > {line}")
                    handle_command(line)
                # Capture output so far
                sys.stdout.seek(0)
                out = sys.stdout.read()
                output_log.append(out)
                sys.stdout.truncate(0)
                sys.stdout.seek(0)
                # Check for expected outputs
                for regex, desc in expected_checks:
                    if not checks_found[desc] and regex.search(out):
                        print(f"[CHECK] {desc} (OK)")
                        checks_found[desc] = True
    except Exception as e:
        print(f"[SCRIPT] Error: {e}")
    finally:
        sys.stdout = orig_stdout
    # Final summary
    print("\n[CHECK SUMMARY]")
    for desc in checks_found:
        print(f"{desc}: {'OK' if checks_found[desc] else 'NOT DETECTED'}")

def repl():
    print('[CLI] Type commands (dcc, sensor, actuator, scenario, run, exit)')
    print('[CLI] Simulation CLI Ready.')
    print('Available commands:')
    print('  help                         Show this help message')
    print('  dcc speed <percent>          Set DCC speed (0–100)')
    print('  dcc function <num> <on|off>  Toggle DCC function number')
    print('  sensor <name> <value>        Set a sensor to a specific value')
    print('  actuator <name> <value>      Set an actuator to a value/state')
    print('  scenario startup             Run the cold-to-working startup scenario')
    print('  run <scriptfile>             Run a script file (see README)')
    print('  exit | quit                  Exit the simulation')
    print("Type 'help' for more details.\n")
    while True:
        try:
            cmd = input('> ')
            if cmd.startswith('run '):
                # run with output checks
                _, fname = cmd.split(None, 1)
                run_script(fname, check_outputs=True)
            else:
                handle_command(cmd)
        except (EOFError, KeyboardInterrupt):
            print('\n[CLI] Exiting simulation.')
            break

"""
dashboard.py

Terminal dashboard UI for the simulation using prompt_toolkit.
Panels:
- Telemetry (top)
- Requested States
- CV Codes
- Command Log (scrollable)
- Command Input (bottom)
"""


from prompt_toolkit.application import Application
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.margins import ScrollbarMargin
import threading
import time

import sim.mock_sensors
import sim.mock_actuators
import sim.mock_dcc
import sim.command_handler

# Placeholder for CVs (replace with real config if available)
CVS = [
    ("42", "Boiler Limit", 110, "°C"),
    ("43", "Superheater Limit", 250, "°C"),
    ("44", "DCC Timeout", 5, "s"),
]

def get_telemetry():
    sensors = sim.mock_sensors.SENSORS
    actuators = sim.mock_actuators.ACTUATORS
    return (
        f"[TELEMETRY]"
        f"\nPressure: {sensors['pressure'].get_value():.2f} bar"
        f"\nTemperature: {sensors['temperature'].get_value():.2f} C"
        f"\nHeater: {actuators['heater'].state}"
    )

def get_requested_states():
    speed = sim.mock_dcc.dcc.speed
    e_stop = sim.mock_dcc.dcc.functions.get(12, False)
    return (
        f"[REQUESTED STATES]"
        f"\nSpeed: {speed} %"
        f"\nE-STOP: {'ON' if e_stop else 'OFF'}"
    )

def get_cv_codes():
    lines = ["[CV CODES]"]
    for num, name, value, unit in CVS:
        lines.append(f"CV{num}: {value} {unit}  ({name})")
    return "\n".join(lines)

# Shared log buffer
action_log = Buffer()

def log_action(msg):
    action_log.insert_text(msg + "\n")

def show_help():
    help_text = (
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
    log_action(help_text)

# Panels
telemetry_area = TextArea(text=get_telemetry(), style="class:telemetry", height=4, read_only=False, focusable=False)
requested_area = TextArea(text=get_requested_states(), style="class:requested", height=3, read_only=False, focusable=False)
cv_area = TextArea(text=get_cv_codes(), style="class:cv", height=5, read_only=False, focusable=False, scrollbar=True)
log_area = Window(BufferControl(buffer=action_log), height=10, wrap_lines=True, right_margins=[ScrollbarMargin()])

# Command auto-completion
command_completer = WordCompleter([
    'help', 'exit', 'quit',
    'dcc speed', 'dcc function',
    'sensor pressure', 'sensor temperature',
    'actuator heater', 'actuator regulator_servo',
    'scenario startup', 'run',
], ignore_case=True, match_middle=True)

input_area = TextArea(height=1, prompt='> ', style="class:input", completer=command_completer, complete_while_typing=True, multiline=False)

# Layout
root_container = HSplit([
    telemetry_area,
    requested_area,
    cv_area,
    log_area,
    input_area
])

layout = Layout(root_container, focused_element=input_area)

# Key bindings
kb = KeyBindings()

@kb.add('c-c')
def _(event):
    event.app.exit()

# Periodic updater for panels

# Periodic sensor/actuator simulation

def sensor_simulation():
    sensors = sim.mock_sensors.SENSORS
    actuators = sim.mock_actuators.ACTUATORS
    safety_shutdown = False
    while True:
        # Simulate heater effect: if heater is ON, increase temperature
        if actuators['heater'].state in ('on', 'ON', True):
            sensors['temperature'].set_value(min(sensors['temperature'].get_value() + 0.5, 150.0))
        else:
            sensors['temperature'].set_value(max(sensors['temperature'].get_value() - 0.2, 20.0))
        # Simulate pressure rising slowly if temperature is high
        if sensors['temperature'].get_value() > 100:
            sensors['pressure'].set_value(min(sensors['pressure'].get_value() + 0.05, 6.0))
        else:
            sensors['pressure'].set_value(max(sensors['pressure'].get_value() - 0.03, 0.0))

        # Safety logic: shutdown if overpressure or overtemperature
        if (sensors['pressure'].get_value() > 4.5 or sensors['temperature'].get_value() > 120) and not safety_shutdown:
            log_action('[SAFETY] Safety shutdown triggered! (Overpressure or overtemperature)')
            actuators['heater'].set_state('off')
            sim.mock_dcc.inject_dcc_command('function', 12, 'on')  # E-STOP
            safety_shutdown = True
        # Reset safety if back in range and E-STOP cleared
        if safety_shutdown and sensors['pressure'].get_value() < 4.0 and sensors['temperature'].get_value() < 110:
            log_action('[SAFETY] Safety shutdown cleared. System back in safe range.')
            sim.mock_dcc.inject_dcc_command('function', 12, 'off')
            safety_shutdown = False
        time.sleep(1)

# UI updater
def updater():
    while True:
        telemetry_area.buffer.text = get_telemetry()
        requested_area.buffer.text = get_requested_states()
        cv_area.buffer.text = get_cv_codes()
        app.invalidate()  # Force full screen redraw
        time.sleep(2)


def run_dashboard():
    threading.Thread(target=sensor_simulation, daemon=True).start()
    threading.Thread(target=updater, daemon=True).start()
    app.run()

# Command handler
def accept(buff):
    cmd = buff.text.strip()
    if cmd:
        log_action(f"[USER] {cmd}")
        sim.command_handler.handle_command(cmd, log_action)
    buff.text = ''

input_area.accept_handler = accept

style = Style.from_dict({
    'telemetry': 'bg:#222244 #ffffff',
    'requested': 'bg:#223322 #ffffff',
    'cv': 'bg:#222222 #ffffaa',
    'input': 'bg:#222222 #ffffff',
})

app = Application(layout=layout, key_bindings=kb, style=style, full_screen=True)

def run_dashboard():
    app.run()

if __name__ == "__main__":
    show_help()
    run_dashboard()

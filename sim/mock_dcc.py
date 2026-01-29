"""
mock_dcc.py

Simulates DCC packet reception and allows injection of DCC commands.
Provides functions to set speed, toggle functions, and log all received commands.
"""

from typing import Callable, Dict

class MockDCC:
    def __init__(self):
        self.speed = 0  # 0-100%
        self.functions = {}  # e.g., {3: True}
        self.on_command = None  # type: Callable[[str, Dict], None]

    def set_speed(self, percent: int):
        self.speed = max(0, min(100, percent))
        self._log_command('speed', {'value': self.speed})

    def set_function(self, fn: int, state: bool):
        self.functions[fn] = state
        self._log_command('function', {'fn': fn, 'state': state})

    def _log_command(self, cmd: str, data: Dict):
        if self.on_command:
            self.on_command(cmd, data)
        else:
            print(f"[DCC] {cmd}: {data}")

# Singleton for use in simulation
dcc = MockDCC()

def inject_dcc_command(cmd: str, *args):
    if cmd == 'speed' and args:
        dcc.set_speed(int(args[0]))
    elif cmd == 'function' and len(args) == 2:
        dcc.set_function(int(args[0]), args[1] in ('on', '1', 'true', 'True'))
    else:
        print(f"[DCC] Unknown command: {cmd} {args}")

# (ensure file ends with a single newline)
"""
conftest.py -- Mocks MicroPython modules for CI and desktop testing.
Ensures that imports like 'import machine' do not fail during pytest or doctest runs.
"""
import sys
from unittest.mock import MagicMock

# List of MicroPython-specific modules to mock
_micropython_modules = [
    "machine",
    "network",
    "esp",
    "esp32",
    "uasyncio",
    "ubluetooth",
    "utime",
    "ujson",
    "uos",
    "neopixel",
    "onewire",
    "ds18x20",
    "binascii",
    "array",
    "struct",
    "micropython",
    "gc",
    # Add more as needed
]
for _mod in _micropython_modules:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()
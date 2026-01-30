"""
Pytest configuration and shared fixtures for locomotive test suite.
"""
import sys
from pathlib import Path
from unittest.mock import Mock
import time as _real_time

# Add parent directory to path for imports (app folder is at project root)
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock MicroPython modules for testing
class MockPin:
    IN = 0
    OUT = 1
    PULL_UP = 2
    IRQ_RISING = 1
    IRQ_FALLING = 2
    
    def __init__(self, pin, mode=None, pull=None):
        self.pin = pin
        self.mode = mode
        self._value = 0
        self._irq_handler = None
    
    def value(self, val=None):
        if val is None:
            return self._value
        self._value = val
        return None
    
    def irq(self, handler=None, trigger=None):
        self._irq_handler = handler

class MockPWM:
    def __init__(self, pin, freq=50):
        self.pin = pin
        self.freq_val = freq
        self._duty = 0
    
    def freq(self, val=None):
        if val is None:
            return self.freq_val
        self.freq_val = val
    
    def duty(self, val=None):
        if val is None:
            return self._duty
        self._duty = val

class MockADC:
    ATTN_11DB = 3
    
    def __init__(self, pin):
        self.pin = pin
        self._value = 2048
    
    def read(self):
        return self._value
    
    def atten(self, val):
        pass

class MockMachine:
    Pin = MockPin
    PWM = MockPWM
    ADC = MockADC
    
    @staticmethod
    def deepsleep():
        pass

# Mock time module with MicroPython functions
class MockTime:
    _ticks = 0
    _real_time_base = None
    _mock_time_base = 0
    
    def __init__(self):
        """Initialize MockTime as module-like object with real-time tracking."""
        self._real_time_base = _real_time.time()
        self._mock_time_base = 0
        self._sleep_time = 0
        # Add standard library attributes for coverage.py compatibility
        self.struct_time = _real_time.struct_time
        self.strftime = _real_time.strftime
        self.localtime = _real_time.localtime
        self.gmtime = _real_time.gmtime
        self.time = self.ticks_ms  # Alias for compatibility
    
    def ticks_ms(self):
        """Return elapsed milliseconds since module load, matching real time during sleep."""
        if self._real_time_base is None:
            self._real_time_base = _real_time.time()
        
        # Calculate actual elapsed time
        elapsed = (_real_time.time() - self._real_time_base) * 1000
        return int(self._mock_time_base + elapsed)
    
    def ticks_us(self):
        """Return elapsed microseconds."""
        return self.ticks_ms() * 1000
    
    @staticmethod
    def ticks_diff(new, old):
        """Calculate difference between two tick values."""
        return new - old
    
    def sleep(self, seconds):
        """Sleep for specified seconds (real sleep for test timing)."""
        _real_time.sleep(seconds)
    
    def sleep_ms(self, ms):
        """Sleep for specified milliseconds (real sleep for test timing)."""
        _real_time.sleep(ms / 1000.0)

# Mock micropython.const() - used in ble_advertising
def mock_const(x, *args):
    """Mock MicroPython const() function - returns value unchanged."""
    return x

# Mock Bluetooth UUID class
class MockUUID:
    def __init__(self, uuid_str):
        self.uuid = uuid_str

# Install mocks before any imports
mock_time_module = MockTime()
sys.modules['machine'] = MockMachine()
sys.modules['time'] = mock_time_module
sys.modules['micropython'] = type('module', (), {'const': mock_const})()
sys.modules['ubluetooth'] = type('module', (), {'BLE': lambda: None})()
sys.modules['bluetooth'] = type('module', (), {
    'BLE': lambda: None,
    'UUID': MockUUID,  # Use class instead of lambda
    'FLAG_NOTIFY': 1,
    'FLAG_WRITE': 2
})()

mock_modules = [
    'machine',
    'micropython',
    'bluetooth',
]
for mod in mock_modules:
    if mod not in sys.modules:
        sys.modules[mod] = mock.MagicMock()

# Mock gc module for memory management
sys.modules['gc'] = type('module', (), {
    'collect': lambda: None,
    'mem_free': lambda: 100000
})()

# Import datetime to ensure coverage.py has access to it
import datetime
sys.modules['datetime'] = datetime

# Pytest fixtures
import pytest

@pytest.fixture(autouse=True)
def reset_mock_time():
    """Reset MockTime before each test for isolated timing."""
    mock_time_module._real_time_base = _real_time.time()
    mock_time_module._mock_time_base = 0
    yield
    # Cleanup after test
    pass

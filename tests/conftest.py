"""
Pytest configuration and shared fixtures for locomotive test suite.
"""
import pytest
import sys
from pathlib import Path
import time as _real_time
from unittest import mock

# Add parent directory to path for imports (app folder is at project root)
sys.path.insert(0, str(Path(__file__).parent.parent))

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
        """
        Get or set pin value (mock).

        Args:
            val: Optional[int] - new value
        Returns:
            int: Current value
        Safety: No hardware change.
        """
        if val is None:
            return self._value
        self._value = val
        return self._value

    def irq(self, handler=None, trigger=None):
        """
        Set IRQ handler for pin (mock).
        Args:
            handler: Callable or None
            trigger: IRQ trigger type (unused)
        Returns:
            None
        Safety: No actual hardware IRQ triggered.
        """
        self._irq_handler = handler

class MockPWM:
    def __init__(self, pin, freq=50):
        self.pin = pin
        self.freq_val = freq
        self._duty = 0

    def freq(self, val=None):
        """
        Get or set PWM frequency (mock).
        Args:
            val: Optional[int] - new frequency
        Returns:
            int: Current frequency
        Safety: No hardware change.
        """
        if val is None:
            return self.freq_val
        self.freq_val = val
        return self.freq_val

    def duty(self, val=None):
        """
        Get or set PWM duty cycle (mock).
        Args:
            val: Optional[int] - new duty cycle
        Returns:
            int: Current duty cycle
        Safety: No hardware change.
        """
        if val is None:
            return self._duty
        self._duty = val
        return self._duty

class MockADC:
    ATTN_11DB = 3

    def __init__(self, pin):
        self.pin = pin
        self._value = 2048

    def read(self):
        """
        Read ADC value (mock).
        Returns:
            int: Simulated ADC value
        Safety: No hardware change.
        """
        return self._value

    def atten(self, val):
        """
        Mock method for ADC attenuation (does nothing).
        Args:
            val: Attenuation value (unused)
        Returns:
            None
        Safety: No hardware change.
        """
        return None

class MockMachine:
    Pin = MockPin
    PWM = MockPWM
    ADC = MockADC
    @staticmethod
    def deepsleep():
        """
        Mock method for deep sleep (does nothing).
        Returns:
            None
        Safety: No hardware change.
        """
        return None

# Mock time module with MicroPython functions
class MockTime:
    _ticks = 0
    _real_time_base = None
    _mock_time_base = 0
    def __init__(self):
        """
        Initialize MockTime as module-like object with real-time tracking.
        """
        self._real_time_base = _real_time.time()
        self._mock_time_base = 0
        self._sleep_time = 0
        self.struct_time = _real_time.struct_time
        self.strftime = _real_time.strftime
        self.localtime = _real_time.localtime
        self.gmtime = _real_time.gmtime
        self.time = self.ticks_ms
    def ticks_ms(self):
        """
        Return elapsed milliseconds since module load, matching real time during sleep.
        """
        if self._real_time_base is None:
            self._real_time_base = _real_time.time()
        elapsed = (_real_time.time() - self._real_time_base) * 1000
        return int(self._mock_time_base + elapsed)
    def ticks_us(self):
        """
        Return elapsed microseconds.
        """
        return self.ticks_ms() * 1000
    @staticmethod
    def ticks_diff(new, old):
        """
        Calculate difference between two tick values.
        """
        return new - old
    def sleep(self, seconds):
        """
        Sleep for specified seconds (real sleep for test timing).
        """
        _real_time.sleep(seconds)
    def sleep_ms(self, ms):
        """
        Sleep for specified milliseconds (real sleep for test timing).
        """
        _real_time.sleep(ms / 1000.0)

def mock_const(x, *args):
    """
    Mock MicroPython const() function - returns value unchanged.
    """
    return x

class MockUUID:
    def __init__(self, uuid_str):
        """
        Initialise mock UUID.
        Args:
            uuid_str: str - UUID string
        Returns:
            None
        Safety: No hardware change.
        """
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

# Pytest fixtures

@pytest.fixture(autouse=True)
def reset_mock_time():
    """
    Reset MockTime before each test for isolated timing.
    """
    # Use public API if available, else fallback to protected
    if hasattr(mock_time_module, 'reset'):
        mock_time_module.reset()
    else:
        # pylint: disable=protected-access
        mock_time_module._real_time_base = _real_time.time()  # noqa: W0212
        mock_time_module._mock_time_base = 0  # noqa: W0212
    yield

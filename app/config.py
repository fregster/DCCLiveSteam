"""
Configuration management for Mallard-ESP32 control system.
Handles CV storage, defaults, and hardware pin mappings.
"""
from typing import Dict
import json
import os

# --- HARDWARE CONSTANTS ---
PWM_FREQ_HEATER = 5000
PWM_FREQ_SERVO  = 50
GC_THRESHOLD    = 61440  # Trigger GC at 60KB free
KPH_TO_CMS      = 27.7778
EVENT_BUFFER_SIZE = 20
ADC_SAMPLES = 10

# Pin Mapping (TinyPICO)
PIN_BOILER = 25
PIN_SUPER  = 26
PIN_SERVO  = 27
PIN_TRACK  = 33
PIN_DCC    = 14
PIN_ENCODER = 32
PIN_PRESSURE = 34
PIN_LOGIC_TEMP = 35

# DCC Timing Constants (microseconds)
DCC_ONE_MIN = 52
DCC_ONE_MAX = 64
DCC_ZERO_MIN = 95
DCC_ZERO_MAX = 119

# File paths
CONFIG_FILE = 'config.json'
ERROR_LOG_FILE = 'error_log.json'

# Mallard Factory Defaults (CV Table)
CV_DEFAULTS = {
    "1": 3,          # DCC Address
    "29": 6,         # Configuration flags
    "30": 1,         # Distress whistle enable
    "31": 0,         # Servo Offset
    "32": 18.0,      # Target Pressure (PSI)
    "33": 35.0,      # Stiction Breakout (%)
    "34": 15.0,      # Slip Sensitivity (%)
    "37": 1325,      # Wheel radius (mm * 100)
    "38": 12,        # Encoder segments
    "39": 203,       # Prototype speed (km/h)
    "40": 76,        # Scale ratio (1:76 OO gauge)
    "41": 75,        # Logic temp limit (°C)
    "42": 110,       # Boiler temp limit (°C)
    "43": 250,       # Superheater temp limit (°C)
    "44": 20,        # DCC timeout (x100ms)
    "45": 8,         # Power timeout (x100ms)
    "46": 77,        # Servo neutral PWM duty
    "47": 128,       # Servo max PWM duty
    "48": 5,         # Whistle offset (degrees)
    "49": 1000       # Servo travel time (ms)
}

def ensure_environment() -> None:
    """
    Checks for existence of config and logs; creates defaults if missing.

    Why: On first boot or after flash erase, the system needs valid configuration
         files to operate safely. Auto-provisioning prevents startup failures.

    Returns:
        None

    Raises:
        OSError: If filesystem is read-only or corrupted

    Safety: Creates factory defaults with conservative safety limits. System cannot
            operate without valid CV table.

    Example:
        >>> ensure_environment()
        >>> os.path.exists('config.json')
        True
    """
    files = os.listdir()
    if CONFIG_FILE not in files:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(CV_DEFAULTS, f)
    if ERROR_LOG_FILE not in files:
        with open(ERROR_LOG_FILE, 'w', encoding='utf-8') as f:
            f.write("[]")

def load_cvs() -> Dict[int, any]:
    """
    Loads CVs into a dictionary with integer keys.

    Why: Configuration Variables (CVs) are stored as JSON strings but accessed
         by integer indices throughout the code. Conversion happens once at load.

    Returns:
        Dictionary with integer keys (CV numbers) and values (CV settings)

    Raises:
        FileNotFoundError: If config.json doesn't exist (call ensure_environment first)
        json.JSONDecodeError: If config file is corrupted

    Safety: Missing or corrupted config file will prevent system startup,
            forcing recreation of safe defaults.

    Example:
        >>> cv = load_cvs()
        >>> cv[42]  # Boiler temp limit
        110
    """
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return {int(k): v for k, v in data.items()}

def save_cvs(cv_table: Dict[int, any]) -> None:
    """
    Persists CV table back to flash storage.

    Why: CV changes (calibration, address programming, safety limits) must survive
         power cycles. Changes only take effect after successful write.

    Args:
        cv_table: Dictionary of CV numbers (int) to values (mixed types)

    Returns:
        None

    Raises:
        TypeError: If cv_table is not a dictionary
        OSError: If flash write fails (filesystem full/corrupted)

    Safety: CRITICAL - Modified safety limits (CV41-45) are written to flash.
            Failed writes leave system with previous (possibly unsafe) values.
            Consider adding write verification.

    Example:
        >>> cv = load_cvs()
        >>> cv[1] = 99  # Change DCC address
        >>> save_cvs(cv)
    """
    if not isinstance(cv_table, dict):
        raise TypeError(f"cv_table must be dict, got {type(cv_table)}")

    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump({str(k): v for k, v in cv_table.items()}, f)

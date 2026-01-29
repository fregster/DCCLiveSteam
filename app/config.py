# Minimum allowed margin between target and max boiler pressure (kPa, not user-configurable)
PRESSURE_MARGIN_KPA = 15.0
"""
Configuration management for ESP32 live steam locomotive control system.
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
# LED pin assignments (update to match hardware wiring)
PIN_FIREBOX_LED = 12  # Example GPIO for firebox LED
PIN_GREEN_LED = 13    # Example GPIO for green status LED

# DCC Timing Constants (microseconds)
DCC_ONE_MIN = 52
DCC_ONE_MAX = 64
DCC_ZERO_MIN = 95
DCC_ZERO_MAX = 119

# File paths
CONFIG_FILE = 'config.json'
ERROR_LOG_FILE = 'error_log.json'

# Factory Defaults (CV Table)
CV_DEFAULTS = {
    "1": 3,          # DCC Address
    "29": 6,         # Configuration flags
    "30": 1,         # Distress whistle enable
    "31": 0,         # Servo Offset
    "32": 124.0,     # Target Pressure (kPa, default 124 kPa; 18.0 PSI reference)
        "35": 207.0,     # Max Boiler Pressure (kPa, user limit, default 207 kPa; 30 PSI reference)
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
    "49": 1000,      # Servo travel time (ms)
    "84": 1,         # Enable Graceful Degradation (1=ON, 0=immediate shutdown)
    "87": 10.0,      # Sensor Failure Decel Rate (cm/s²)
    "88": 20,        # Degraded Mode Timeout (seconds)
    "51": 4.5,       # Power Budget (Amps)
    "52": 1,         # Speed Control Mode (0=Direct throttle, 1=Feedback speed control)
}

def ensure_environment() -> None:
    """
    Checks for existence of config and logs; creates defaults if missing.

    Why:
        Ensures the system always has valid configuration and error log files on boot.
        Prevents startup failures due to missing files after flash erase or first boot.

    Args:
        None

    Returns:
        None

    Raises:
        OSError: If filesystem is read-only or corrupted

    Safety:
        Creates factory defaults with conservative safety limits. System cannot
        operate without valid CV table. Prevents unsafe operation due to missing config.

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

    Why:
        Configuration Variables (CVs) are stored as JSON strings but accessed
        by integer indices throughout the code. Conversion happens once at load.

    Args:
        None

    Returns:
        Dictionary with integer keys (CV numbers) and values (CV settings)

    Raises:
        FileNotFoundError: If config.json doesn't exist (call ensure_environment first)
        json.JSONDecodeError: If config file is corrupted

    Safety:
        Missing or corrupted config file will prevent system startup,
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


# CV Validation Bounds (Safety-Critical)
# Format: cv_number: (min_value, max_value, unit, description)
CV_BOUNDS = {
    1: (1, 127, "addr", "DCC address"),
    29: (0, 255, "flags", "Configuration flags"),
    30: (0, 1, "bool", "Distress whistle enable"),
    31: (-50, 50, "pwm", "Servo offset"),
    32: (70.0, 207.0, "kPa", "Target pressure (user, kPa; default 124 kPa; 18.0 PSI reference)",),
    35: (100.0, 220.0, "kPa", "Max boiler pressure (user, kPa; default 207 kPa; 30 PSI reference, Hornby safety valve)"),
    33: (10.0, 50.0, "%", "Stiction breakout"),
    34: (5.0, 30.0, "%", "Slip sensitivity"),
    37: (1000, 2000, "mm*100", "Wheel radius"),
    38: (8, 16, "segments", "Encoder segments"),
    39: (100, 250, "km/h", "Prototype speed"),
    40: (50, 120, "ratio", "Scale ratio"),
    41: (60, 85, "°C", "Logic temp limit"),
    42: (100, 120, "°C", "Boiler temp limit"),
    43: (240, 270, "°C", "Superheater temp limit"),
    44: (5, 100, "x100ms", "DCC timeout"),
    45: (2, 50, "x100ms", "Power timeout"),
    46: (40, 120, "pwm", "Servo neutral duty"),
    47: (80, 160, "pwm", "Servo max duty"),
    48: (0, 20, "deg", "Whistle offset"),
    49: (500, 3000, "ms", "Servo travel time"),
    84: (0, 1, "bool", "Graceful degradation enable"),
    87: (5.0, 20.0, "cm/s²", "Sensor failure decel rate"),
    88: (10, 60, "s", "Degraded mode timeout"),
}


def validate_and_update_cv(cv_num: int, new_value: str, cv_table: Dict[int, any]) -> tuple[bool, str]:
    """
    Validates CV number and value against safe bounds before update.

    Why: Prevents unsafe CV values that could cause thermal runaway, servo damage,
    or system instability. Conservative bounds prevent operator errors during
    over-the-air configuration via BLE.

    Args:
        cv_num: CV number (integer, must be in CV_BOUNDS)
        new_value: New value as string (will be parsed to int/float)
        cv_table: Current CV dictionary (will be modified on success)

    Returns:
        (True, "Updated CV{num} to {value}") on success
        (False, "CV{num} out of range {min}-{max} {unit}") on validation failure

    Raises:
        ValueError: If new_value cannot be parsed as number
        KeyError: If cv_num not in CV_BOUNDS (unknown CV)

    Safety:
        - Rejects CV numbers not in CV_BOUNDS dictionary
        - Rejects values outside hardcoded min/max limits
        - Preserves old value on error (atomic update)
        - Returns detailed error messages for operator feedback

    Example:
        >>> cv = load_cvs()
        >>> success, msg = validate_and_update_cv(32, "20.0", cv)
        >>> success
        True
        >>> msg
        'Updated CV32 to 20.0 PSI'
        >>> success, msg = validate_and_update_cv(32, "30.0", cv)
        >>> success
        False
        >>> msg
        'CV32 out of range 15.0-25.0 PSI'
    """
    # Check if CV number is known
    if cv_num not in CV_BOUNDS:
        return (False, f"CV{cv_num} unknown (not in validation table)")

    min_val, max_val, unit, description = CV_BOUNDS[cv_num]

    try:
        # Parse value (try float first, fall back to int)
        parsed_value = float(new_value)
        # If the value is an integer string, store as int
        if parsed_value.is_integer():
            parsed_value = int(parsed_value)
    except (ValueError, AttributeError):
        return (False, f"CV{cv_num} invalid value '{new_value}' (not a number)")

    # Validate against bounds
    if not (min_val <= parsed_value <= max_val):
        return (False, f"CV{cv_num} out of range {min_val}-{max_val} {unit}")

    # Update CV table (atomic)
    old_value = cv_table.get(cv_num, "unset")
    cv_table[cv_num] = parsed_value

    return (True, f"Updated CV{cv_num} ({description}) from {old_value} to {parsed_value} {unit}")

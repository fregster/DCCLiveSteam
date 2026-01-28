# DCC Function Reference

This document describes the DCC function mapping and the Python module API.

---

## DCC Function Mapping

| Function | Logic Assignment | Behaviour | Description |
|----------|------------------|-----------|-------------|
| F0 | Lights / Master | Toggle | Enables/Disables internal lighting and wakes the logic from standby. |
| F1 | Steam Sound | Active | Triggers the sound-card sync (if equipped) or background hiss logic. |
| F2 | Whistle | Momentary | Moves the servo into the CV48 zone for high-pressure venting. |
| F3 | Boiler Heat | Toggle | Enables/Disables the PIN 25 PWM heating element. |
| F4 | Superheater | Toggle | Enables/Disables the PIN 26 PWM secondary heating element. |
| F5 | Brake Release | Toggle | Overrides the regulator to allow movement (Safety Lock). |
| F6 | Aux / Injector | Pulse | Logic trigger for an auxiliary water pump or smoke generator. |
| F8 | Mute / Silent | Toggle | Silences all diagnostic beeps and sound-card outputs. |
| F10 | Telemetry | Toggle | Enables/Disables high-speed BLE data streaming to save power. |
| F12 | Full E-Stop | Momentary | Triggers the `die("USER_ESTOP")` sequence immediately. |

---

## Python Module API Reference

### `app.config` - Configuration Management

#### `ensure_environment() -> None`
Checks for existence of config and logs; creates defaults if missing.

**Returns:** None  
**Raises:** `OSError` if filesystem is read-only or corrupted  
**Safety:** Creates factory defaults with conservative safety limits.

#### `load_cvs() -> Dict[int, Any]`
Loads CVs into a dictionary with integer keys.

**Returns:** Dictionary with integer keys (CV numbers) and values (CV settings)  
**Raises:** 
- `FileNotFoundError` if config.json doesn't exist
- `json.JSONDecodeError` if config file is corrupted

#### `save_cvs(cv_table: Dict[int, Any]) -> None`
Persists CV table back to flash storage.

**Args:**
- `cv_table`: Dictionary of CV numbers (int) to values (mixed types)

**Raises:**
- `TypeError` if cv_table is not a dictionary
- `OSError` if flash write fails

---

### `app.main` - Locomotive Orchestrator

#### `class Locomotive`
Master Controller Orchestrator for locomotive subsystems.

**Methods:**

##### `__init__(cv: Dict[int, Any]) -> None`
Initialise all locomotive subsystems.

**Args:**
- `cv`: CV configuration table loaded from config.json

**Safety:** All subsystems start in safe state (heaters off, servo neutral).

##### `log_event(event_type: str, data: Any) -> None`
Adds event to circular buffer (max 20 entries).

**Args:**
- `event_type`: Event category string ("SHUTDOWN", "BOOT", etc.)
- `data`: Event-specific data (cause string, CV values, sensor readings)

**Safety:** Buffer capped at 20 entries. Written to flash on die() for persistence.

##### `die(cause: str, force_close_only: bool = False) -> None`
Emergency Shutdown Sequence.

**Args:**
- `cause`: Shutdown reason ("LOGIC_HOT", "DRY_BOIL", "SUPER_HOT", "PWR_LOSS", "DCC_LOST", "USER_ESTOP")
- `force_close_only`: If True, only closes regulator. If False, full shutdown.

**Safety:** Six-stage shutdown or instant regulator close for E-STOP.

#### `run() -> None`
Main execution loop - 50Hz control cycle.

**Safety:** Watchdog.check() called every loop iteration for <100ms detection latency.

---

### `app.sensors` - Sensor Suite

#### `class SensorSuite`
Manages all ADC sensors (thermistors, voltage, pressure, encoder).

**Methods:**

##### `__init__() -> None`
Initialise all ADC pins and encoder interrupt.

##### `read_temps() -> Tuple[float, float, float]`
Reads all three NTC thermistors with oversampling.

**Returns:** Tuple of (boiler_temp_C, superheater_temp_C, logic_temp_C)  
**Safety:** Returns 999.9°C on sensor failure to trigger thermal shutdown.

##### `read_track_voltage() -> int`
Reads rectified DCC voltage (5:1 divider).

**Returns:** Track voltage in millivolts (0-3600mV for 0-18V DCC)

##### `read_pressure() -> float`
Reads pressure transducer (0.5-4.5V = 0-100 PSI).

**Returns:** Pressure in PSI (0-100 range)  
**Raises:** `ValueError` if ADC reading out of valid range

##### `update_encoder() -> int`
Returns cumulative encoder count (ISR-driven).

**Returns:** Total encoder pulses since boot (0-2^31)

---

### `app.physics` - Physics Engine

#### `class PhysicsEngine`
Converts DCC speed commands to regulator positions using prototypical physics.

**Methods:**

##### `__init__(cv: Dict[int, Any]) -> None`
Initialise with scale ratio and prototype speed.

**Args:**
- `cv`: CV table with keys 39 (prototype speed), 40 (scale ratio)

##### `speed_to_regulator(dcc_speed: int) -> float`
Converts DCC speed step (0-127) to regulator percentage (0-100%).

**Args:**
- `dcc_speed`: DCC speed command (0-127)

**Returns:** Regulator position as percentage (0.0-100.0)

##### `calc_velocity(encoder_delta: int, time_ms: int) -> float`
Calculates locomotive velocity from encoder readings.

**Args:**
- `encoder_delta`: Change in encoder count since last update
- `time_ms`: Time elapsed in milliseconds

**Returns:** Velocity in cm/s  
**Safety:** Returns 0.0 if time_ms is zero (prevents division by zero).

---

### `app.actuators` - Actuator Control

#### `class MechanicalMapper`
Handles smooth regulator movement with slew-rate limiting.

**Methods:**

##### `__init__(cv: Dict[int, Any]) -> None`
Initialise servo controller with neutral position.

**Args:**
- `cv`: CV table with keys 46 (min PWM), 47 (max PWM), 49 (travel time)

##### `set_goal(percent: float, whistle: bool, cv: Dict[int, Any]) -> None`
Sets target regulator position.

**Args:**
- `percent`: Target position (0-100%)
- `whistle`: If True, move to whistle position (CV48)
- `cv`: CV configuration table

##### `update(cv: Dict[int, Any]) -> None`
Processes slew-rate limiting and applies duty cycle.

**Args:**
- `cv`: CV configuration table

**Safety:** Emergency mode bypasses slew rate for instant closure.

#### `class PressureController`
PID controller for boiler pressure regulation.

**Methods:**

##### `__init__(cv: Dict[int, Any]) -> None`
Initialise PID controller with target pressure.

**Args:**
- `cv`: CV table with key 33 (target pressure PSI)

##### `update(pressure: float, dt: float) -> None`
Updates PID control and heater PWM duty cycles.

**Args:**
- `pressure`: Current pressure in PSI
- `dt`: Time delta in seconds

**Safety:** Anti-windup prevents integral term saturation.

##### `shutdown() -> None`
Immediately disables all heaters (emergency shutdown).

---

### `app.safety` - Watchdog System

#### `class Watchdog`
Monitors CV-defined thermal and signal thresholds.

**Methods:**

##### `__init__() -> None`
Initialise watchdog timers.

##### `check(t_logic: float, t_boiler: float, t_super: float, track_v: int, dcc_active: bool, cv: Dict[int, Any], loco: Any) -> None`
Checks all safety parameters and triggers shutdown if thresholds exceeded.

**Args:**
- `t_logic`: Logic bay temperature (°C)
- `t_boiler`: Boiler shell temperature (°C)
- `t_super`: Superheater tube temperature (°C)
- `track_v`: Track voltage (mV)
- `dcc_active`: True if valid DCC packet received recently
- `cv`: CV configuration table (keys 41-45)
- `loco`: Locomotive instance (for calling die())

**Safety:** Calls loco.die() with appropriate cause string on threshold violation.

---

### `app.dcc_decoder` - DCC Signal Processing

#### `class DCCDecoder`
NMRA DCC packet decoder with ISR-driven signal processing.

**Methods:**

##### `__init__(cv: Dict[int, Any]) -> None`
Initialise DCC decoder with address and attach ISR.

**Args:**
- `cv`: CV table with keys 1 (address), 17/18 (long address), 29 (config flags)

##### `is_active() -> bool`
Checks if valid DCC packet received within timeout.

**Returns:** True if DCC signal active, False if timeout  
**Safety:** Timeout configurable via CV44 (default 500ms).

**Attributes:**
- `current_speed`: Current speed command (0-127)
- `direction`: True=forward, False=reverse
- `whistle`: True if F2 (whistle) active
- `e_stop`: True if E-STOP command received

---

### `app.ble_uart` - BLE Telemetry

#### `class BLE_UART`
Nordic UART Service for wireless telemetry.

**Methods:**

##### `__init__(name: str = "Locomotive") -> None`
Initialise BLE UART service.

**Args:**
- `name`: BLE device name (default: "Locomotive")

##### `advertise() -> None`
Starts BLE advertising.

##### `send_telemetry(velocity: float, pressure: float, temps: Tuple[float, float, float], servo: int) -> None`
Queues telemetry data for non-blocking transmission.

**Args:**
- `velocity`: Current velocity (cm/s)
- `pressure`: Current pressure (PSI)
- `temps`: Tuple of (boiler, super, logic) temperatures (°C)
- `servo`: Current servo PWM duty cycle

##### `process_telemetry() -> None`
Sends queued telemetry (non-blocking, <5ms).

**Safety:** Queue prevents blocking main control loop.

##### `is_connected() -> bool`
Checks if BLE client is connected.

**Returns:** True if connected, False otherwise

---

## See Also

- [CV.md](CV.md) - Complete Configuration Variable reference
- [capabilities.md](capabilities.md) - System capabilities and features
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment instructions
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions
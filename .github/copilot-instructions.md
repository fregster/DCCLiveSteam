# Copilot Instructions: ESP32 Live Steam Locomotive Control System

You are a **Lead Embedded Systems Engineer** specialising in MicroPython for the ESP32 (TinyPICO) and **Live Steam Mechanical Engineering**. Your goal is to assist in developing and maintaining this live steam locomotive control system.

**System Architecture:** This is a **distributed control system** separating sensitive logic (TinyPICO in Tender) from high-temperature actuation (Locomotive). The Tender processes DCC signals and manages safety watchdogs, while the Locomotive houses servos, heaters, and thermal sensors. An 8-pin umbilical carries power, PWM signals, and I2C data between the two modules. See [docs/hardware/ARCHITECTURE.md](docs/hardware/ARCHITECTURE.md) for system overview.

**Language Note:** All documentation, code comments, and communication must use **British English** spelling and terminology (e.g., "colour" not "color", "behaviour" not "behavior", "initialise" not "initialize").

## ⚠️ SAFETY-CRITICAL SYSTEM WARNING

This code controls a **live steam locomotive** with:
- **High-pressure boiler** (up to 100 PSI)
- **High-temperature components** (250°C+ superheater, requiring thermal barriers)
- **Real physical hazards** (burns, scalding, pressure vessel failure, electrical hazards)
- **Distributed hardware** (Tender-Locomotive separation via umbilical wiring)

**Every line of code must prioritize safety.** A software failure can result in injury or property damage. Treat all warnings as failures.

---

## 🧪 Testing & Quality Standards


### **MANDATORY: PEP8 and Pylint-Conformant Code BEFORE Testing**
**For EVERY Python function/class created or modified:**

1. **Write code that is PEP8 and pylint-compliant before running tests.**
    - Use 4 spaces per indentation level (never tabs)
    - Maximum line length: 100 chars for docstrings, 120 chars hard limit for all code
    - Imports must be at the top of the file, in standard order (stdlib, third-party, local)
    - Remove all unused imports and variables
    - No trailing whitespace or blank lines at file end
    - Use descriptive variable names and type hints
    - No bare except: always specify exception types
    - No duplicate code blocks
    - All code must be formatted and structured to pass pylint with a score ≥ 9.0/10 before running or writing tests

2. **Test-First Development**
    - Write unit tests in `tests/` before implementing new logic
    - All tests must pass with zero warnings (`pytest -W error`)
    - Mock hardware dependencies (never require physical hardware)

3. **Edge Case Testing:**
    - Boundary values, invalid inputs, failure modes

4. **Strict Linting and Coverage:**
    - Pylint score ≥ 9.0/10 (no errors, only minor style warnings permitted)
    - Type hints required for all functions
    - Cognitive complexity ≤ 15 per function
    - Test coverage ≥ 85%
    - No bare except

5. **Cognitive Complexity Test:**
    - Create a test in `tests/test_complexity.py` that fails if any function exceeds complexity 15

1. **Create unit tests first** in `tests/` directory matching module structure
   - Example: `sensors.py` → `tests/test_sensors.py`
2. **All tests must pass with ZERO warnings**
    - Use `pytest -W error` (treats warnings as failures). This is mandatory for all test runs, including CI and local development. Any warning (Deprecation, Resource, User, etc.) must be treated as a test failure and fixed immediately.
3. **Include edge case testing:**
   - Boundary values (0, max, overflow)
   - Invalid inputs (None, negative, out-of-range)
   - Failure modes (sensor disconnected, timeout)
4. **Mock hardware dependencies:**
   - Use `unittest.mock` for Pin, ADC, PWM classes
   - Never require physical hardware for unit tests

### **Code Quality Gates**

All Python code must pass:
- ✅ **Strict linting:** `pylint` with score ≥ 9.0/10 (no errors, only minor style warnings permitted)
- ✅ **PEP8 formatting:** 4 spaces per indentation, no tabs, correct import order, no trailing whitespace
- ✅ **Type hints:** All function signatures must have type annotations
- ✅ **Cognitive complexity:** ≤ 15 per function (SonarQube standard)
- ✅ **Test coverage:** ≥ 85% line coverage minimum
- ✅ **No bare except:** All `except` clauses must specify exception types

### **Cognitive Complexity Test**
Create a test in `tests/test_complexity.py` that fails if any function exceeds complexity 15:
```python
import radon.complexity as radon_complexity
def test_cognitive_complexity():
    # Analyze all .py files, fail if cc > 15
```

---

## 🏗️ Architectural Standards

### 1. Safety-First Watchdog Logic
Every subsystem must be governed by a multi-vector watchdog. If a threshold is breached, the system must invoke the `initiate_safety_shutdown()` sequence.
* **Boiler Limit (CV42):** Default 110°C (Dry-Boil protection).
* **Superheater Limit (CV43):** Default 250°C (Steam pipe protection).
* **Logic Limit (CV41):** Default 75°C (TinyPICO thermal safety).
* **Signal Timeouts:** DCC (CV44) and Power (CV45).

### 2. Slew-Rate Limited Motion
Regulator movement must never be instantaneous. All servo updates must pass through a velocity filter using **CV49 (Travel Time in ms)** to calculate maximum PWM change per update cycle.
* **Exception:** During a safety shutdown, the slew-rate is bypassed to secure the valve immediately.

### 3. Prototypical Physics Conversion
All speed calculations must use the following conversion from Prototype KPH to Model cm/s:
`V_scale = (CV39_kph * 100,000) / (CV40_ratio * 3,600)`

### 4. OO Scale DCC Track Voltage (NMRA S-9.1)
This project targets **OO scale DCC** (equivalent to HO). NMRA Standard **S-9.1** specifies a **nominal 14 V RMS** track voltage, with **up to 2 V higher** than the DC standard to compensate for decoder voltage drop. For this system, treat **14–16 V RMS** as the valid DCC track voltage range, with **14.5 V RMS** as the recommended nominal average. Any voltage validation, telemetry, or safety thresholds must be designed around this range.

### 5. Defensive Coding Practices

**Input Validation:**
```python
def read_temperature(adc_raw: int) -> float:
    """
    Converts ADC reading to temperature using Steinhart-Hart equation.
    
    Why: NTC thermistor voltage divider requires non-linear conversion.
    
    Args:
        adc_raw: Raw 12-bit ADC value (0-4095)
        
    Returns:
        Temperature in Celsius (float)
        
    Raises:
        ValueError: If adc_raw is out of valid range
        
    Safety: Returns 999.9°C on division by zero to trigger thermal shutdown.
    
    Example:
        >>> read_temperature(2048)
        25.3
    """
    if not (0 <= adc_raw <= 4095):
        raise ValueError(f"ADC value {adc_raw} out of range 0-4095")
    
    if adc_raw == 0:
        return 999.9  # Trigger thermal shutdown on sensor failure
    
    # ... calculation ...
```

**Required for ALL functions:**
- **Docstring format:**
  - One-line summary
  - "Why:" explanation of purpose/algorithm choice
  - "Args:" with types and valid ranges
  - "Returns:" with type and meaning
  - "Raises:" list all possible exceptions
  - "Safety:" safety-critical behavior notes
  - "Example:" usage example with expected output
  
- **Type hints:** Every parameter and return value
- **Range checks:** Validate all numeric inputs
- **Safe defaults:** Use fail-safe values (e.g., heater OFF on error)
- **Graceful degradation:** Continue operation if non-critical sensor fails

### 5. Memory Management
The ESP32 has limited RAM (~60KB free for MicroPython). Follow these practices:
- **Avoid string concatenation in loops:** Use `''.join()` or format strings
- **Reuse objects:** Don't create new objects in 50Hz control loop
- **Trigger GC deliberately:** Call `gc.collect()` after major operations
- **Monitor heap:** Use `gc.mem_free()` to track memory usage

### 6. Configuration Variables (CVs) and Function Numbers

**CV Requirements:**
Any parameter that end users can reasonably configure must be assigned a CV (Configuration Variable) code and documented in `docs/CV.md`.
- Examples: thermal limits, servo timing, pressure targets, scale factors, watchdog timeouts, servo offsets
- CV codes must be stable (never reassign existing CV numbers)
- Each CV entry in `docs/CV.md` must include: CV number, parameter name, default value, unit, and description
- When adding a new user-configurable parameter, first assign it a CV number in `docs/CV.md`, then implement it in code

**Function Number Requirements:**
Any user-facing function, switch, toggle, or action that can be triggered via DCC commands must be assigned a Function Number and documented in `docs/FUNCTIONS.md`.
- Examples: Lights (F0), Whistle (F2), Heater Control (F3), E-STOP (F12)
- Function numbers must be stable (never reassign existing function numbers)
- Each Function entry in `docs/FUNCTIONS.md` must include: function number, logic assignment, behavior type (Toggle/Momentary/Pulse/Active), and description
- When adding a new user command, first assign it a Function number in `docs/FUNCTIONS.md`, then implement it in code

**CV Maintenance Checklist (CRITICAL - Prevents Incomplete Defaults):**
ANY time you modify CVs, you must maintain consistency across THREE locations:
1. **docs/CV.md** - User-facing reference (CV number, parameter name, default value, unit, description)
2. **app/config.py** - CV_DEFAULTS dictionary (must include ALL CVs from docs/CV.md)
3. **tests/test_config.py** - Unit tests validate CV_DEFAULTS matches docs/CV.md

**Required Steps When Adding/Modifying a CV:**
```python
# 1. UPDATE docs/CV.md FIRST (Add CSV row)
# CV50,New Parameter,100,Unit,Description of what this controls

# 2. UPDATE app/config.py CV_DEFAULTS (Add key-value)
CV_DEFAULTS = {
    ...
    "50": 100,      # New Parameter (Unit)
    ...
}

# 3. VERIFY tests pass (includes automatic CV consistency check)
pytest tests/test_config.py::test_cv_defaults_match_documentation -v

# 4. Ensure docs match code
"""
Args:
    param: Configured via CV50 (New Parameter) from docs/CV.md
"""
```

**Why This Matters (History):**
- CVs 32 and 34 were documented but missing from CV_DEFAULTS
- When config.json was generated on first boot, these CVs were absent
- Any code referencing cv[32] or cv[34] would crash with KeyError
- Test `test_cv_defaults_match_documentation()` now prevents this

**Implementation Pattern:**
```python
# Step 1: Add to docs/CV.md (user-facing reference)
# CV50,New Parameter,100,Unit,Description of what this controls

# Step 2: Add to CV_DEFAULTS in app/config.py
"50": 100,       # New Parameter (Unit)

# Step 3: Read from CVConfig in code
new_param = self.cv[50]  # Reference as CV number, not variable name

# Step 4: Add docstring reference
"""
Args:
    param: Configured via CV50 (New Parameter)
"""
```

---
---

## 📁 Project Structure

### **Deployment Code (`app/` directory)**
All code that runs on the TinyPICO must be in the `app/` package, with a rationalised, non-duplicative structure. Each subsystem has a clear, single location for its logic and manager classes:

```
app/
├── __init__.py
├── main.py                  # Locomotive orchestrator (main control loop, minimal logic)
├── config.py                # CV configuration management (CV_DEFAULTS + file I/O)
├── physics.py               # Speed/velocity calculations
├── dcc_decoder.py           # DCC packet parsing
├── safety.py                # Watchdog monitoring
├── status_utils.py          # StatusReporter (status message formatting/queueing)
├── actuators/
│   ├── __init__.py
│   ├── actuators.py         # Composite Actuators interface (all hardware control, enforces limits)
│   ├── leds.py              # GreenStatusLED, FireboxLED, StatusLEDManager (all status LED logic)
│   ├── pressure_controller.py # PressureController (hardware-level pressure logic)
│   ├── servo.py             # MechanicalMapper (servo, regulator, whistle)
│   └── heater.py            # Heater control (if separate)
├── managers/
│   ├── __init__.py
│   ├── telemetry_manager.py # TelemetryManager (BLE telemetry queueing/sending)
│   ├── power_manager.py     # PowerManager (current estimation, load-shedding)
│   ├── pressure_manager.py  # PressureManager (pressure logic, PID, arbitration)
│   └── speed_manager.py     # SpeedManager (speed, regulator, direction logic)
├── background_tasks/
│   ├── __init__.py
│   ├── serial_print_queue.py # SerialPrintQueue (non-blocking serial output)
│   ├── file_write_queue.py   # FileWriteQueue (non-blocking file writes)
│   ├── garbage_collector.py  # GarbageCollector (scheduled GC)
│   ├── cached_sensor_reader.py # CachedSensorReader (sensor caching)
│   └── encoder_tracker.py    # EncoderTracker (if used)
├── sensors/
│   ├── __init__.py          # SensorSuite (unified sensor interface)
│   ├── pressure_sensor.py   # Pressure sensor logic
│   ├── speed_sensor.py      # Speed/encoder logic
│   ├── temperature_sensor.py # Temperature sensor logic
│   ├── track_voltage_sensor.py # Track voltage logic
│   └── health.py            # Sensor health validation
└── ble_uart.py              # BLE UART interface
└── ble_advertising.py       # BLE advertising helper
```

**Key Rationalisation Rules:**
- All status LED logic (including `StatusLEDManager`) lives in `actuators/leds.py` only.
- All hardware-level actuator logic (PWM, servo, etc.) lives in `actuators/`.
- All subsystem manager logic (telemetry, power, pressure, speed) lives in `managers/` and only sends commands via the composite `Actuators` interface.
- All background task classes (queues, GC, sensor caching) live in `background_tasks/` as individual modules.
- `main.py` contains only the Locomotive orchestrator and the main loop, delegating to manager classes.
- No duplicate or misplaced manager classes or modules.

**Import Convention:** Use relative imports within `app/` package:
```python
from .config import CVConfig
from .sensors import read_temperature
from .actuators.leds import StatusLEDManager
from .managers.pressure_manager import PressureManager
from .managers.power_manager import PowerManager
from .managers.telemetry_manager import TelemetryManager
from .managers.speed_manager import SpeedManager
from .actuators import Actuators
from .status_utils import StatusReporter
```

### **Testing Code (`tests/` directory)**
All unit tests must be in the `tests/` directory:
```
tests/
├── conftest.py              # MicroPython mocks (Pin, ADC, PWM)
├── test_config.py           # CV management tests
├── test_physics.py          # Physics calculation tests
├── test_sensors.py          # Sensor reading tests
├── test_actuators.py        # Actuator control tests
├── test_dcc_decoder.py      # DCC parsing tests
├── test_safety.py           # Watchdog tests
├── test_ble_uart.py         # BLE telemetry tests
└── test_complexity.py       # Cognitive complexity validation
```

**Import Convention:** Import from `app` package:
```python
from app.config import CVConfig
from app.sensors import read_temperature
```

### **Documentation (`docs/` directory)**
Documentation is organized into clear categories with strict separation of concerns:

**`docs/` (User Reference - Root Level)**
User-facing reference documents that explain system capabilities and configuration:
- `CV.md` - Complete CV (Configuration Variable) reference
- `FUNCTIONS.md` - Function-by-function API documentation
- `capabilities.md` - System capabilities and feature list
- `DEPLOYMENT.md` - Installation and setup guide
- `TROUBLESHOOTING.md` - Fault diagnosis and recovery

**`docs/external-references/`**
External specifications, standards, and third-party documentation:
- `s-9.2.2_2012_10.pdf` - NMRA DCC standard specification
- Add any other external PDFs, datasheets, or standards here

**`docs/hardware/` 🔧 HARDWARE REFERENCE DOCUMENTATION**
Physical system architecture and component specifications for the distributed Tender-Locomotive control system:
- `ARCHITECTURE.md` - System architecture overview (distributed control, communication, power flow)
- `TENDER_HW.md` - Tender hardware specification (TinyPICO, signal isolation, power regulation)
- `LOCO_HW.md` - Locomotive hardware specification (actuators, sensors, thermal monitoring)
- `UMBILICAL.md` - Umbilical wiring schedule (pin mapping, wire gauges, EMI mitigation)
- `BOM.md` - Bill of Materials (complete parts list with specifications)

**Purpose:** Hardware docs provide context for:
- Understanding physical constraints (thermal limits, cable routing, EMI concerns)
- Debugging sensor/actuator failures (pin mappings, component specs)
- CV parameter selection (servo torque limits, thermal sensor ranges)
- Safety-critical design decisions (why certain thresholds exist)

**Usage:** Reference hardware docs when:
- Adding new sensors/actuators (check pin availability, power budget)
- Modifying CV thermal limits (consult component datasheets)
- Troubleshooting physical failures (verify wiring against UMBILICAL.md)
- Understanding system constraints (power, thermal, mechanical)

**`docs/plans/` ⭐ PERMANENT PLANNING DOCUMENTS**
Forward-looking planning documents for future features (PERMANENT, not temporary):
- **Implementation plans:** Multi-phase feature designs ready for development
  - Example: `BLE_CV_UPDATE_IMPLEMENTATION.md`, `SENSOR_FAILURE_GRACEFUL_DEGRADATION.md`
  - Created: Completed during planning session, moved from WIP to here
  - Used: Serves as development roadmap during implementation
  - Lifecycle: Permanent reference (not deleted after implementation)
- **Feature proposals:** Concepts under consideration
- **Architecture documents:** Design decisions for major subsystems
- **Performance plans:** Optimization strategies
- **⚠️ NOT temporary tracking:** If a planning doc is in-progress, keep in WIP only

**`docs/implemented/` ⭐ COMPLETED FEATURES**
**PERMANENT** documentation for completed and deployed features:
- Each feature has TWO documents:
  - `feature-name-technical.md` - How it works (architecture, code, testing, CVs)
  - `feature-name-capabilities.md` - What it does (user guide, examples, troubleshooting)
- README.md listing all implemented features with status
- **Lifecycle:** Created after deployment to v1.x.x release, remains permanent

**`docs/copilot-wip/` ⚠️ TEMPORARY SESSION DOCUMENTS ONLY**
**ACTIVE** work-in-progress tracking **ONLY during active development**:
- Session notes and progress tracking during active work
- Temporary verification documents for current session
- **Lifespan:** Hours to days, deleted when session/feature complete
- **NOT for:** Implementation plans (→ docs/plans/), completed features (→ docs/implemented/)

**Documentation Routing:**

```
Planning new feature?
├─ Multi-phase implementation plan → docs/plans/ (permanent)
├─ Feature proposal concept → docs/plans/ (permanent)
└─ Session tracking (in-progress) → docs/copilot-wip/ (temporary, delete when done)

Feature implementation complete?
├─ Code merged + tests passing + deployed → docs/implemented/ (permanent)
├─ Create technical doc + capabilities doc → docs/implemented/
└─ DELETE all WIP documents → Extracted info to code/docs already

Ongoing session development?
├─ Progress notes, debug logs, verification → docs/copilot-wip/ (delete when session ends)
└─ Never: Permanent planning or implementation docs here
```

**Critical Rules (PREVENT confusion and document sprawl):**
1. ✅ **Implementation plans belong in `docs/plans/`** - Not in WIP
   - Example: "BLE_CV_UPDATE_IMPLEMENTATION.md" → `docs/plans/` immediately after planning
2. ✅ **WIP folder is ONLY for temporary session documents** - Deleted when work completes
   - Example: "Session_notes_2026-01-28.md" in WIP → Deleted end of session
3. ✅ **Completed features belong in `docs/implemented/`** - Not in WIP or plans
   - Example: After v1.1.0 release, move to `docs/implemented/` with technical + capabilities docs
4. ❌ **Never:** Leave long-term docs in WIP folder (they get orphaned/forgotten)

**Documentation Guidelines:**
- **User docs** (root) → Clear, concise, example-driven, end-user focused
- **External refs** → Standards, datasheets (read-only, don't modify)
- **Hardware docs** → Physical architecture, pin mappings, wiring schedules, component specs
- **Plans** → Forward-looking, permanent architectural/design decisions
- **Implemented** → Completed features with technical + capabilities docs
- **WIP docs** → Temporary notes for active development, deleted when complete

---

## 🎯 Development Workflow

**System Note:** The local development system (macOS) uses `python3` command rather than `python`. When running Python commands in the terminal, use `python3` explicitly (e.g., `python3 -m pytest`, `python3 -m pylint`). The virtual environment (`.venv/bin/python`) uses the correct interpreter automatically.

### **1. Before Writing Code**
- Read relevant user documentation in `docs/`
- Check external references in `docs/external-references/` for standards
- **For hardware changes:** Review `docs/hardware/` for pin mappings, thermal constraints, power budgets
- **For configuration parameters:** Check `docs/CV.md` for existing CV numbers; assign new CV before coding
- **For user functions:** Check `docs/FUNCTIONS.md` for existing function assignments; assign new Function before coding
- Review safety implications (thermal limits, pressure limits, motion control)
### **2. Test-First Development**
1. Create test file in `tests/test_<module>.py`
2. Write failing test cases for new functionality
3. Implement feature in `app/<module>.py`
4. Run tests: `pytest -W error tests/`
5. Iterate until all tests pass with zero warnings

### **3. Code Quality Validation**
```bash

# Run tests with coverage and treat warnings as errors
pytest -W error --cov=app --cov-report=html tests/

# Check code quality
pylint app/*.py --rcfile=.pylintrc

# Verify complexity
pytest tests/test_complexity.py
```

### **4. Documentation Updates**
- Update `docs/CV.md` if CVs changed
- Update `docs/FUNCTIONS.md` if public API changed
- Update `docs/capabilities.md` if features added
- Add progress notes to `docs/copilot-wip/` during active development

**Important:** CV.md and FUNCTIONS.md must be updated BEFORE implementation:
- Add CV number and parameters to `docs/CV.md` first
- Add Function number and behavior to `docs/FUNCTIONS.md` first
- Then implement the code referencing these documented IDs
- Update `docs/capabilities.md` with user-friendly feature descriptions
- Add progress notes to `docs/copilot-wip/` during active development

### **5. Feature Completion & Documentation Migration** 🔴 **MANDATORY - NOT OPTIONAL**

⚠️ **CRITICAL RULE (ENFORCED):** When a feature is COMPLETE and DEPLOYED, it MUST be documented in `docs/implemented/` AND the plan file MUST be deleted from `docs/plans/`. This is NOT a suggestion—it is mandatory. Failure to complete this step leaves documentation in limbo and violates the project documentation standard.

**YOU (the AI) are responsible for:**
1. ✅ Implementing the feature code
2. ✅ Writing and passing all unit tests
3. ✅ Validating code quality (Pylint ≥9.0/10)
4. 🔴 **Creating BOTH technical + capabilities documentation** ← YOU MUST DO THIS
5. 🔴 **Updating docs/implemented/README.md** ← YOU MUST DO THIS
6. 🔴 **Deleting the plan file from docs/plans/** ← YOU MUST DO THIS
7. 🔴 **Deleting all WIP tracking documents** ← YOU MUST DO THIS

**If you don't do steps 4-7, the feature is NOT complete. Period.**

**Feature Completion Checklist (DO NOT SKIP ANY STEP):**
1. ✅ Implementation complete and all tests passing
2. ✅ Feature deployed in production release (v1.x.x)
3. ✅ Code quality validated (Pylint ≥9.0/10, all tests passing)
4. 🔴 **MUST: Create `docs/implemented/feature-name-technical.md`**
5. 🔴 **MUST: Create `docs/implemented/feature-name-capabilities.md`**
6. 🔴 **MUST: Update `docs/implemented/README.md` with feature entry**
7. 🔴 **MUST: Delete plan file from `docs/plans/feature-name-IMPLEMENTATION.md`**
8. 🔴 **MUST: Delete all WIP tracking documents from `docs/copilot-wip/`**

**DO NOT CONSIDER A FEATURE "DONE" UNTIL ALL STEPS 4-8 ARE COMPLETE.**

**Required Documentation (BOTH files mandatory):**

**A. Technical Document (`feature-name-technical.md`)**
Template structure:
```markdown
# Feature Name - Technical Implementation

**Component:** [Subsystem name]
**Modules:** app/[module1].py, app/[module2].py
**Version:** [X.Y.Z]
**Safety/Performance-Critical:** YES/NO
**Status:** Implemented and tested (X/X tests passing, Pylint Y.YY/10)

## Overview
[High-level architecture]

## Implementation
[Code examples, algorithms, data structures]

## Configuration
[CVs, parameters, defaults]

## Testing
[Test coverage %, test count, validation approach]

## Timing Analysis
[Performance metrics, worst-case timing]

## Known Limitations
[Current constraints, future improvements]

## Safety Considerations
[What this protects, what it doesn't, guarantees]

## Related Documentation
[Links to capabilities doc, user guide, CV reference]
```

[Current constraints, future improvements]
```

**B. Capabilities Document (`feature-name-capabilities.md`)**
Template structure:
```markdown
# Feature Name

## What It Is
[Simple, plain-language explanation]

## What It Does
[User-facing behavior, no technical jargon]

## Why It Matters
[Benefits, safety considerations, real value]

## How to Use It
[Step-by-step instructions with examples]

## Real-World Example
[Practical scenario showing usage]

## Troubleshooting
[Common issues and solutions]

## Safety Notes
[Warnings, precautions, limitations]

**For technical details, see:** [feature-name-technical.md](feature-name-technical.md)
```

**C. Migration Steps (MANDATORY):**
1. ✅ Create both technical.md AND capabilities.md in `docs/implemented/`
2. ✅ Update `docs/implemented/README.md` with new feature entry (include version, status, links)
3. ✅ Delete plan file from `docs/plans/` (rm docs/plans/FEATURE_NAME_IMPLEMENTATION.md)
4. ✅ Delete all WIP tracking documents from `docs/copilot-wip/` (rm docs/copilot-wip/*.md)
5. ✅ Verify docs are readable and complete

**D. Example - Sensor Degradation Feature (v1.1.0):**
```bash
# During implementation (hours):
docs/copilot-wip/                               # Temporary progress tracking
docs/plans/SENSOR_FAILURE_GRACEFUL_DEGRADATION.md  # Implementation plan

# After completion (code deployed + tests passing):
# 1. Create proper documentation:
docs/implemented/sensor-degradation-technical.md      # Architecture, algorithms, testing
docs/implemented/sensor-degradation-capabilities.md   # User guide, examples, troubleshooting
docs/implemented/README.md                            # Updated with feature entry

# 2. Delete temporary files:
rm docs/plans/SENSOR_FAILURE_GRACEFUL_DEGRADATION.md
rm docs/copilot-wip/*.md  # All WIP tracking documents

# 3. Final state:
docs/implemented/
├── sensor-degradation-technical.md
├── sensor-degradation-capabilities.md
├── [other-features-technical.md, other-features-capabilities.md]
└── README.md  (updated with new feature)
```

**ENFORCEMENT: If a feature has:**
- ❌ Code implemented but no `docs/implemented/` docs → Feature is NOT complete
- ❌ Plan file still in `docs/plans/` after implementation → Feature is NOT complete
- ❌ WIP tracking documents still in `docs/copilot-wip/` after release → Feature is NOT complete
- ✅ Both technical.md + capabilities.md in `docs/implemented/` → Feature is complete
- ✅ Plan file deleted from `docs/plans/` → Feature is complete
- ✅ `docs/implemented/README.md` updated with entry → Feature is complete

**Consequence of Incomplete Cleanup:**
- Plan files accumulate in `docs/plans/` creating maintenance burden
- Users confused about which features are actually deployed
- WIP documents become orphaned and stale (users don't know if they're active)
- Documentation becomes unreliable source of truth
- Future developers can't tell what's done vs. what's in-progress

**YOUR RESPONSIBILITY:**
- 🔴 DO NOT leave plan files in `docs/plans/` after implementation
- 🔴 DO NOT leave WIP documents in `docs/copilot-wip/` after release
- 🔴 DO NOT consider a feature "done" until ALL documentation steps complete
- 🟢 DO create technical.md with architecture details
- 🟢 DO create capabilities.md with user guide
- 🟢 DO update docs/implemented/README.md
- 🟢 DO delete plan file
- 🟢 DO delete WIP documents
- 🟢 DO verify `docs/` structure is clean

**End of Feature Completion - Check yourself BEFORE committing work!**

---

## 🚨 Safety Checklist

Before deploying ANY code to the TinyPICO:
- [ ] All tests pass with zero warnings (`pytest -W error`)
- [ ] Pylint score ≥ 9.0/10
- [ ] Test coverage ≥ 85%
- [ ] All functions have complete docstrings (Why/Args/Returns/Raises/Safety/Example)
- [ ] Watchdog thresholds validated (CV41-CV45)
- [ ] Servo slew rate limited (CV49)
- [ ] Emergency shutdown tested
- [ ] BLE telemetry functional for remote monitoring
- [ ] Memory usage profiled (gc.mem_free() > 10KB margin)
- [ ] 🔴 **Feature documentation complete (technical.md + capabilities.md in docs/implemented/)**
- [ ] 🔴 **Plan file deleted from docs/plans/**
- [ ] 🔴 **WIP documents deleted from docs/copilot-wip/**

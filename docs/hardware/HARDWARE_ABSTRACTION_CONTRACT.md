# Hardware Abstraction Interface Contract

**Location:** app/hardware_interfaces.py

## Overview
All hardware access (GPIO, ADC, PWM, etc.) must be encapsulated behind the following interfaces:
- `ISensor`: For all sensor devices (temperature, pressure, encoder, voltage, etc.)
- `IActuator`: For all actuator devices (servos, heaters, LEDs, etc.)

No direct use of hardware primitives (e.g., `machine.Pin`, `machine.ADC`, `machine.PWM`) is permitted outside the `actuators/` and `sensors/` packages. The only exception is for communication libraries (e.g., BLE), which may access hardware directly in their own modules.

## Interface Definitions

### ISensor
- Must implement `read() -> Any` to return the current sensor value.
- May implement `health() -> bool` to report sensor health.
- Must raise an exception on unsafe or out-of-range values.

### IActuator
- Must implement `set(value: Any) -> None` to set the actuator state.
- May implement `status() -> Any` to report actuator status or feedback.
- Must raise an exception on unsafe or out-of-range values.

## Usage Pattern
- All hardware drivers in `actuators/` and `sensors/` must implement these interfaces.
- The main application, managers, and orchestrators interact only with these interfaces, never with hardware primitives directly.
- Unit tests and mocks must use these interfaces for testability.

## Rationale
- Enforces safety, testability, and maintainability.
- Prevents accidental or unsafe direct hardware access.
- Enables mocking and simulation for unit tests.

## Enforcement
- Code reviews and lint/test rules must ensure no direct hardware access outside allowed modules.
- Violations must be refactored immediately.

---

For interface code, see [app/hardware_interfaces.py](../../app/hardware_interfaces.py).

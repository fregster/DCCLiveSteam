## 3.6 Servo and Sensor Mounting Requirements

**Servo Mounting:**
- Use rigid mounting bracket to prevent flex under load
- Minimum stall torque: 2.0 kg·cm (MG90S meets requirement)
- Ensure servo horn is aligned with valve spindle at neutral position
- Avoid exposure to direct steam or radiant heat (mount behind thermal barrier if possible)
- Use thread-locking compound on all mounting screws to prevent loosening from vibration

**Thermal Sensor Mounting:**
- Thermocouple/IR sensor must be clamped to target surface with thermal paste for best response
- Maintain minimum 10mm clearance from high-voltage wiring
- Route sensor cables away from heater elements and moving linkages

**Pressure Sensor Placement:**
- Mount on steam line with vibration-damping grommet
- Avoid direct contact with superheater or boiler shell
- Use PTFE tape on all threaded connections to prevent leaks
## 3.5 MOSFET Gate Drive Circuit

Each IRLZ44N requires:

```
ESP32 GPIO ──[100Ω]──┬─ MOSFET Gate
                     │
                    [10kΩ] Pull-down to GND
                     │
                    GND
```

* **100Ω Gate Resistor:** Limits gate charging current to ~30mA (safe for ESP32)
* **10kΩ Pull-down:** Ensures MOSFET OFF during ESP32 boot/reset
* **Flyback Diode:** 1N4007 across heater coil (cathode to V+, anode to drain)
  - Clamps inductive kickback when MOSFET switches OFF
  - Critical for preventing voltage spikes that could damage MOSFET

**Circuit Protection:**
* Heater coils are inductive loads; flyback protection is mandatory
* Without flyback diode, back-EMF can exceed 100V during turn-off transients
* Diode must be rated for heater current (minimum 1A, 1N4007 rated 1A continuous)
## 3.3 Thermal Sensor Configuration

| Sensor | I2C Address | Target Surface | Field of View | Temp Range |
|:-------|:------------|:---------------|:--------------|:-----------|
| MLX90614 #1 (Boiler) | 0x5A (Factory default) | Boiler shell | 90° cone | -40°C to 125°C |
| MLX90614 #2 (Superheater) | 0x5B (Reprogrammed) | Steam pipe | 90° cone | -40°C to 385°C (Extended range variant) |

**Important:** Use MLX90614ESF-DCI variant for Superheater (extended temperature range). Standard MLX90614ESF-BAA variant saturates at 125°C.

**Mounting Requirements:**
- Minimum clearance: 10mm from target surface
- Maximum range: 50mm (accuracy degrades beyond this distance)
- Avoid direct line-of-sight to flames or radiant heat sources
# 3. Locomotive Hardware Specification

## 3.1 Actuation & Thermal Module
The Locomotive houses the physical components required for steam regulation and environmental monitoring. The superheater is electrically heated, and steam arrives from the tender boiler via the steam pipe.

| Component | Specification | Purpose |
| :--- | :--- | :--- |
| **Regulator Servo** | MG90S Metal Gear | High-torque mechanical valve actuation. |
| **Superheater Thermocouple** | Type-K + Amplifier | Direct temperature monitoring of superheater. |
| **Pressure Sensor** | 0–200 PSI Transducer | Boiler pressure monitoring (via steam line). |
| **Odometry** | TCRT5000 IR Sensor | Optical wheel-rotation counting for speed feedback. |

## 3.2 Locomotive Pin Mapping
* **Pin 27 (PWM):** Regulator Servo (Motion control).
* **I2C Bus:** Shared data lines for thermocouple amplifier (and digital pressure sensor if fitted).
* **Analogue Input:** Pressure sensor analogue output (if using analogue transducer).
* **Digital Input:** Speed pulse from TCRT5000.

## 3.3 Sensor Configuration (Locomotive)

**Superheater Thermocouple:**
* Type-K thermocouple mounted to superheater pipe
* Use a dedicated thermocouple amplifier module (I2C or SPI)
* **Important:** Ensure the amplifier address or chip select is unique on the bus

**Pressure Sensor:**
* 0–200 PSI transducer mounted to steam line (remote from high-temperature components)
* Analogue output is preferred for noise immunity over the umbilical
* Use a pull-down resistor at the ESP32 input to avoid floating readings when disconnected

**Mounting Requirements:**
* Thermocouple junction must be mechanically clamped to the superheater pipe
* Keep pressure sensor body away from heater elements and insulate with a thermal barrier
* Cable routing must avoid contact with hot surfaces and moving linkage

## 3.4 Odometry Sensor Mounting

**TCRT5000 Optical Gap:** 2.5mm ± 0.5mm
* Too close: Sensor saturates, cannot distinguish reflective vs. absorptive surfaces
* Too far: Insufficient signal strength, erratic pulse detection
* Recommended: Mount sensor fixed, attach reflective tape to wheel rim at 8 equal intervals

**Pulse Rate Calculation:**
* Wheel diameter: 32mm (example for 7¼" gauge)
* 8 reflectors per revolution
* At 10 km/h (prototype speed):
  - Model speed: 10 km/h / 29.26 (1:29.26 scale) = 0.342 km/h = 95 mm/s
  - Wheel RPM: (95 mm/s × 60) / (π × 32 mm) = 56.6 RPM
  - Pulse frequency: 56.6 RPM × 8 pulses = 453 Hz (well within TCRT5000 response time)
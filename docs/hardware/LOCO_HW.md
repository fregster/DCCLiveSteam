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
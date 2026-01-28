# ESP32 Live Steam Locomotive Controller
**A high-fidelity MicroPython control system for live-steam locomotives featuring triple-vector safety watchdogs, slew-rate limited servo regulation, and BLE diagnostics.**

[![Tests](https://img.shields.io/badge/tests-116%20passed-brightgreen)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-89%25-brightgreen)](.coveragerc)
[![Code Quality](https://img.shields.io/badge/pylint-10.00%2F10-brightgreen)](app/)
[![Version](https://img.shields.io/badge/version-1.0.0-blue)](CHANGELOG.md)
[![MicroPython](https://img.shields.io/badge/MicroPython-v1.20+-blue)](https://micropython.org/)
[![Hardware](https://img.shields.io/badge/hardware-TinyPICO%20ESP32-orange)](https://www.tinypico.com/)

---

## 🚀 Quick Start

### Prerequisites
- **TinyPICO** ESP32 board
- **MicroPython v1.20+** firmware
- **Python 3.8+** with `ampy` and `esptool` installed
- Live steam locomotive with servo-controlled regulator

### Installation (5 Minutes)
```bash
# 1. Install tools
pip install esptool adafruit-ampy

# 2. Flash MicroPython firmware
esptool.py --port /dev/ttyUSB0 erase_flash
esptool.py --chip esp32 --port /dev/ttyUSB0 write_flash -z 0x1000 esp32-*.bin

# 3. Upload application
cd DCCLiveSteam
ampy --port /dev/ttyUSB0 put app
ampy --port /dev/ttyUSB0 put main.py

# 4. Reboot and verify
screen /dev/ttyUSB0 115200
# Should see: "LOCOMOTIVE CONTROLLER BOOTING..."
```

**See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for complete installation guide.**

---

## 🛠 Project Overview
This ESP32-based controller is a production-grade firmware solution (specifically optimized for the TinyPICO) to manage the complexities of live-steam model locomotives. Unlike standard motor-based DCC decoders, this system integrates real-world physics, thermal safety monitoring, and precision mechanical regulation.

### Architecture
```
┌─────────────────────────────────────────────────┐
│           50Hz Control Loop (main.py)           │
├─────────────────────────────────────────────────┤
│  Sensors → Physics → Watchdog → Actuators       │
│    ↓         ↓         ↓           ↓            │
│  ADC      Velocity   Safety    Servo + PWM      │
│  NTC      Calc       Monitor   Heater           │
│  Pressure DCC Map    Thermal                    │
│  Encoder             Timeouts                   │
└─────────────────────────────────────────────────┘
     ↑                                    ↓
  DCC Input                          BLE Telemetry
  (ISR-driven)                       (Non-blocking)
```

## ✨ Key Features
* **Prototypical Physics Engine:** Automatically translates Prototype KPH and Scale Ratios into precise model velocity (cm/s).
* **Slew-Rate Limited Regulation:** Implements velocity-limited servo control to protect delicate regulator linkages from mechanical shock (CV49).
* **Triple-Vector Safety Watchdog:** Active monitoring of:
    * **Boiler Health:** Dry-boil protection (110°C default).
    * **Steam Quality:** Superheater pipe protection (250°C default).
    * **Silicon Safety:** Logic bay/ESP32 thermal guard (75°C default).
* **Mechanical Failsafe:** Automated "Distress Whistle" blow-off sequence during power loss or thermal breach.
* **Memory Management:** Threshold-based Garbage Collection (GC) and circular event buffer (20 entries) for long-term stability.
* **BLE Telemetry:** Real-time diagnostics via Nordic UART Service (velocity, pressure, temperatures, servo position).
* **DCC Compliance:** NMRA S-9.2.2 compatible with 128-step speed control and function mapping (F0-F12).

---

## 📊 System Status

| Metric | Status |
|--------|--------|
| **Tests** | 106/106 passing (100%) |
| **Coverage** | 89% (exceeds 85% target) |
| **Code Quality** | Pylint 10.00/10 |
| **Complexity** | All functions ≤ 15 (SonarQube standard) |
| **Safety Audit** | Phase 2 complete ✅ |
| **Documentation** | Complete ✅ |

---

## 📋 Configuration Variable (CV) Reference

Key CVs for tuning (see [docs/CV.md](docs/CV.md) for complete reference):

| CV | Parameter | Default | Unit | Description |
| :--- | :--- | :--- | :--- | :--- |
| **1** | DCC Address | 3 | ID | Short address (1-127) |
| **33** | Stiction Breakout | 35.0 | % | Momentary kick to start motion |
| **39** | Prototype Speed | 203 | km/h
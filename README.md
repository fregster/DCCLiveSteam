# ESP32 Live Steam Locomotive Controller
**A high-fidelity MicroPython control system for live-steam locomotives featuring triple-vector safety watchdogs, slew-rate limited servo regulation, and BLE diagnostics.**

---

## 🛠 Project Overview
This ESP32-based controller is a production-grade firmware solution (specifically optimized for the TinyPICO) to manage the complexities of live-steam model locomotives. Unlike standard motor-based DCC decoders, this system integrates real-world physics, thermal safety monitoring, and precision mechanical regulation.

[Image of a system architecture diagram for a live-steam locomotive control system]

## ✨ Key Features
* **Prototypical Physics Engine:** Automatically translates Prototype KPH and Scale Ratios into precise model velocity ($cm/s$).
* **Slew-Rate Limited Regulation:** Implements a background task to limit the servo's rotational speed, protecting delicate regulator linkages from mechanical shock (CV49).
* **Triple-Vector Safety Watchdog:** Active monitoring of:
    * **Boiler Health:** Dry-boil protection ($110°C$).
    * **Steam Quality:** Superheater pipe protection ($250°C$).
    * **Silicon Safety:** Logic bay/ESP32 thermal guard ($75°C$).
* **Mechanical Failsafe:** Automated "Distress Whistle" blow-off sequence powered by Supercapacitor reserves during power loss or thermal breach.
* **Memory Management:** Threshold-based Garbage Collection (GC) and chunked RAM-to-Flash event logging to ensure long-term stability without heap fragmentation.

---

## 📋 Configuration Variable (CV) Reference
These values are stored in non-volatile storage and allow for precision field tuning without code modification.

| CV | Parameter | Default | Description |
| :--- | :--- | :--- | :--- |
| **33** | Stiction Breakout | 35.0 | % Regulator "kick" to start motion from a standstill. |
| **39** | Prototype Speed | 203 | Max speed in **km/
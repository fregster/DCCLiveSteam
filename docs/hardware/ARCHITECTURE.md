## 1.4 Fault Tolerance & Recovery
* **Umbilical Disconnection:** Locomotive defaults to safe state (regulator closed, heaters OFF)
* **I2C Timeout:** 100ms watchdog per transaction; fallback to last known good value
* **Power Loss:** Supercapacitor provides minimum 3 seconds at 200mA load for controlled shutdown

# 1. System Architecture

## 1.1 Concept of Operations

This is a distributed control system for live-steam locomotives. It separates sensitive logic and signal processing (Tender) from high-heat actuation and environment sensing (Locomotive).

**Controller Board:** All references to the control MCU now refer to the Pimoroni TinyPICO ESP32 (ESP32-PICO-D4), 4MB flash, 520KB SRAM, 3.3V logic, USB-C, and LiPo support. See TENDER_HW.md for details.

**Model-specific note (no firebox):**
* This is a model with **no real firebox**. All heat is generated electrically in the boiler and the superheater.
* Cautions relating to open flames or a firebox do **not** apply.

**Steam flow path:**
* Steam is generated in the **tender boiler** (electrically heated).
* Steam passes through the **steam pipe** to the **locomotive superheater**.
* From the superheater, steam continues to the **steam chest/steambox** and cylinders.


**Hornby Live Steam layout:**
* **Tender:** Boiler, keep-alive supercapacitors, boiler thermocouple, water level sensor, and power MOSFETs
* **Locomotive:** Superheater, regulator servo, superheater thermocouple, pressure sensor, and odometry sensor

**MCU Note:** The system is now standardised on the Pimoroni TinyPICO ESP32 (ESP32-PICO-D4) board. All GPIO, power, and logic references are to this board unless otherwise specified.



## 1.2 Communication & Power Flow
* **Data Ingress:** DCC track signals are isolated via a high-speed optocoupler before reaching the ESP32.
* **Signal Processing:** The TinyPICO applies CV-based logic (Slew-rate, KPH conversion, Safety Watchdogs).
* **Actuation:** Heater PWM power (from tender-mounted MOSFETs), servo PWM, and sensor data are sent through an 8-pin umbilical to the locomotive.
* **Power Management:** Track voltage (17V+) is stepped down to 5V for logic, with a supercapacitor bank providing a 2-5 second "Stay-Alive" window for emergency shutdowns.

## 1.3 Timing Specifications
* **I2C Bus Speed:** 100 kHz (Standard Mode) for noise immunity
* **PWM Frequency:**
	- Heater Control: 5 kHz (ultrasonic, reduces audible noise)
	- Servo Control: 50 Hz (standard RC servo timing)
* **Main Loop:** 50 Hz (20ms cycle time, synchronised with servo updates)
* **Thermal Sensor Polling:** 10 Hz (100ms intervals, sufficient for thermal inertia)

**Note:** UK DCC track voltage is nominally 14V AC (RMS) as per NMRA S-9.1, not 17V. All power and safety calculations should use 14–16V RMS as the design range.
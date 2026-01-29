# 1. System Architecture

## 1.1 Concept of Operations
This is a distributed control system for live-steam locomotives. It separates sensitive logic and signal processing (Tender) from high-heat actuation and environment sensing (Locomotive).

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



## 1.2 Communication & Power Flow
* **Data Ingress:** DCC track signals are isolated via a high-speed optocoupler before reaching the ESP32.
* **Signal Processing:** The TinyPICO applies CV-based logic (Slew-rate, KPH conversion, Safety Watchdogs).
* **Actuation:** Heater PWM power (from tender-mounted MOSFETs), servo PWM, and sensor data are sent through an 8-pin umbilical to the locomotive.
* **Power Management:** Track voltage (17V+) is stepped down to 5V for logic, with a supercapacitor bank providing a 2-5 second "Stay-Alive" window for emergency shutdowns.
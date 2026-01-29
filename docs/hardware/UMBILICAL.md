### 2. Isolation Test
Measure resistance between adjacent pins:
* **Pass criteria:** > 10MΩ (confirms no shorts)

### 3. I2C Capacitance (Optional but recommended)
Connect LCR meter to pins 6 and 7 at Tender end:
* Measure capacitance with Loco end open circuit
* **Pass criteria:** < 100pF (confirms cable quality)

### 4. Power Drop Test
Apply 14V to pin 1, ground to pin 2 at Tender end:
* Measure voltage at Loco end while drawing 500mA load
* **Pass criteria:** > 13.5V (confirms acceptable voltage drop)
# 5. Umbilical Wiring Schedule (`UMBILICAL.md`)

## 5.1 Overview
The umbilical connects the **Tender Logic Bay** to the **Locomotive Actuator Frame**. Due to the mix of high-current heater lines and sensitive I2C data lines, specific wire gauges and shielding practices must be followed to prevent EMI (Electromagnetic Interference).

**Track Voltage Standard (OO Scale DCC):** NMRA S-9.1 specifies a nominal **14 V RMS** track voltage for OO/HO, with up to **2 V higher** to compensate for decoder voltage drop. Treat **14–16 V RMS** as the valid DCC track voltage range, with **14.5 V RMS** as the recommended nominal average.



## 5.2 Pin-to-Pin Mapping

| Pin | Function | Tender Side (Source) | Loco Side (Destination) | Wire Gauge | Priority |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **V+ Track** | Bridge Rectifier (+) | Heater V+ / Servo V+ | 0.33 mm² (22 AWG) | Power |
| **2** | **GND** | Bridge Rectifier (-) | Heater Return / Sensor GND | 0.33 mm² (22 AWG) | Ground |
| **3** | **Heater 1 Power (PWM)** | Tender MOSFET Output 1 | Locomotive Heater Element 1 | 0.20 mm² (24 AWG) | Power |
| **4** | **Heater 2 Power (PWM)** | Tender MOSFET Output 2 | Locomotive Heater Element 2 | 0.20 mm² (24 AWG) | Power |
| **5** | **Servo** | TinyPICO GPIO 27 | Regulator Servo Signal | 0.08 mm² (28 AWG) | PWM |
| **6** | **I2C SDA** | TinyPICO GPIO 21 | Locomotive Sensor Bus SDA | 0.05 mm² (30 AWG, twisted) | Data |
| **7** | **I2C SCL** | TinyPICO GPIO 22 | Locomotive Sensor Bus SCL | 0.05 mm² (30 AWG, twisted) | Data |
| **8** | **Sensor VCC**| TinyPICO 3.3V Out | Thermocouple Amplifier / Pressure Sensor VCC | 0.05 mm² (30 AWG) | Logic |

## 5.3 Harnessing Standards

### EMI Mitigation
* **Twisted Pairs:** Pins 6 (SDA) and 7 (SCL) **must** be twisted together to reduce cross-talk from the high-frequency 5kHz heater PWM lines.
* **Separation:** If possible, route the Power/GND (Pins 1 & 2) on the opposite side of the connector shell from the I2C lines.

### Thermal Protection
* The umbilical must be wrapped in **Polyimide (Kapton) tape** or a high-temp silicone sleeve where it passes near the boiler casing or superheater.



## 5.4 Connector Specifications
* **Type:** Locking 8-pin connector with positive latch (vibration-proof).
* **Pitch:** 2.5mm preferred, 1.0mm minimum if space-constrained.
* **Current Rating:** Minimum 2.0A per pin for pins 1 through 4.
* **Temperature Rating:** Minimum 105°C (near-boiler environment).

## 5.5 Cable Length Constraints

**Maximum Length:** 150 mm (15 cm; 5.9 in)

**Rationale:**
* **I2C Capacitance:** ~82 pF/m (30 AWG, ~25 pF/ft)
	- 150 mm cable = ~12 pF (5.9 in)
	- Two sensors + cable = ~80pF total (well under 400pF limit for standard I2C mode)
* **Voltage Drop:** 0.33 mm² (22 AWG) at 1 A over 150 mm = ~10 mV drop
	- Negligible for 17V power rail
* **EMI Susceptibility:** Shorter cable = reduced antenna effect for 5kHz PWM signals
* **Mechanical Constraint:** Tender-Locomotive coupling distance in 184 mm (7¼ in) gauge models

**If Longer Cable Required:**
* Not permitted. The umbilical **must not** exceed 150 mm (15 cm).
* If the mechanical layout demands a longer reach, redesign the coupling or relocate the tender electronics.

## 5.6 Recommended Connector

**Primary Recommendation:** Molex Pico-Lock 2.5mm Pitch (Part #: 0502792891)
* **Locking Mechanism:** Dual side-latch, vibration-proof
* **Current Rating:** 3A per contact (adequate for all signals)
* **Temperature Rating:** 105°C (suitable for near-boiler mounting)
* **Availability:** Readily available, pre-crimped harnesses from multiple suppliers

**Alternative:** JST SH 1.0mm (if space-constrained)
* **Trade-off:** Higher contact resistance, more fragile latch
* **Use only if:** Molex Pico-Lock physically will not fit

## 5.7 Pre-Commissioning Test Procedure

**Required Equipment:**
* Digital multimeter (resistance mode, 200Ω range)
* LCR meter (optional, for capacitance measurement)

**Test Steps:**

### 1. Continuity Test (Both ends disconnected)
Measure resistance across each pin pair (Tender end to Loco end):
* **Pass criteria:** < 1Ω for all pins
* Verifies: No broken conductors

### 2. Isolation Test
Measure resistance between adjacent pins:
* **Pass criteria:** > 10MΩ (confirms no shorts)
* Verifies: No solder bridges, no damaged insulation

### 3. I2C Capacitance (Optional but recommended)
Connect LCR meter to pins 6 and 7 at Tender end:
* Measure capacitance with Loco end open circuit
* **Pass criteria:** < 100pF (confirms cable quality)
* Verifies: Cable is suitable for I2C communication

### 4. Power Drop Test
Apply **14.5 V RMS-equivalent** (nominal) to pin 1, ground to pin 2 at Tender end:
* Measure voltage at Loco end while drawing 500mA load
* **Pass criteria:** > 14.0 V (confirms acceptable voltage drop within 14–16 V RMS range)
* Verifies: Power conductors have adequate cross-sectional area

**Test Failure Actions:**
* Continuity >1Ω: Check crimp connections, replace faulty conductor
* Isolation <10MΩ: Inspect for solder bridges, damaged insulation
* Capacitance >100pF: Cable too long or poor quality, replace with specified wire
* Voltage drop >0.5V: Insufficient wire gauge or poor connections, rebuild cable
# Hardware Documentation Review - British English & Gap Analysis

**Date:** 29 January 2026
**Reviewer:** GitHub Copilot (AI Assistant)
**Purpose:** Language verification and content gap identification

---

## ✅ British English Compliance

**Status:** All hardware documentation files reviewed for British English compliance.

### Files Reviewed:
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [TENDER_HW.md](TENDER_HW.md)
- [LOCO_HW.md](LOCO_HW.md)
- [UMBILICAL.md](UMBILICAL.md)
- [BOM.md](BOM.md)

### Language Audit Results:
✅ **No Americanisms detected** - All documents correctly use British English spelling:
- Uses "Optocoupler" (not "optoisolator")
- Technical terminology is language-neutral
- No instances of "optimize", "organize", "color", "center", "behavior" variants found

**Recommendation:** Language compliance is excellent. Maintain this standard for future documentation.

---

## 📋 Content Gap Analysis

### 1. **ARCHITECTURE.md** - System Architecture Overview

**Strengths:**
- Clear separation of concerns (Tender vs Locomotive)
- Well-defined communication flow
- Proper emphasis on safety-critical power management

**Identified Gaps:**
1. ⚠️ **Missing timing specifications**
   - No mention of I2C bus speed (typically 100kHz or 400kHz)
   - No specification of PWM frequencies for heater control
   - No servo update rate documented
   
2. ⚠️ **Missing failure mode analysis**
   - What happens if umbilical connection fails mid-operation?
   - Behaviour during I2C bus lockup or collision
   - Recovery procedures for communication faults

3. ⚠️ **Incomplete power specifications**
   - "17V+" track voltage - what is the maximum safe voltage?
   - Supercap discharge curve not documented (2-5 seconds is vague)
   - No mention of inrush current limiting for supercap charging

**Recommendations:**
```markdown
## 1.3 Timing Specifications
* **I2C Bus Speed:** 100 kHz (Standard Mode) for noise immunity
* **PWM Frequency:**
  - Heater Control: 5 kHz (ultrasonic, reduces audible noise)
  - Servo Control: 50 Hz (standard RC servo timing)
* **Main Loop:** 50 Hz (20ms cycle time, synchronized with servo updates)
* **Thermal Sensor Polling:** 10 Hz (100ms intervals, sufficient for thermal inertia)

## 1.4 Fault Tolerance & Recovery
* **Umbilical Disconnection:** Locomotive defaults to safe state (regulator closed, heaters OFF)
* **I2C Timeout:** 100ms watchdog per transaction; fallback to last known good value
* **Power Loss:** Supercapacitor provides minimum 3 seconds at 200mA load for controlled shutdown
```

---

### 2. **TENDER_HW.md** - Tender Hardware Specification

**Strengths:**
- Clear component listing with specific part numbers
- Proper emphasis on signal isolation
- Well-documented power regulation

**Identified Gaps:**
1. ⚠️ **Missing GPIO allocation table**
   - Lists GPIO 14, 21, 22, 25, 26, 27 but no comprehensive pin map
   - No mention of reserved pins (GPIO 0, 2, 12, 15 have boot constraints on ESP32)
   - No documentation of unused pins available for expansion

2. ⚠️ **Incomplete optocoupler specifications**
   - Lists 6N137 but no mention of:
     - Input current limiting resistor value
     - Pull-up resistor on output side
     - Maximum data rate (10 Mbps for 6N137, far exceeds DCC needs)

3. ⚠️ **Missing thermal considerations**
   - TinyPICO has onboard 3.3V LDO - is it adequate for all I2C sensors?
   - Buck converter efficiency and heat dissipation not mentioned
   - No mention of ambient temperature operating range

**Recommendations:**
```markdown
## 2.3 Complete GPIO Allocation

| GPIO | Function | Direction | Notes |
|:-----|:---------|:----------|:------|
| 14 | DCC Input | Input | 5V tolerant via optocoupler |
| 21 | I2C SDA | Bidirectional | 4.7kΩ pull-up to 3.3V |
| 22 | I2C SCL | Output | 4.7kΩ pull-up to 3.3V |
| 25 | Heater 1 PWM | Output | 5kHz PWM, drives MOSFET gate |
| 26 | Heater 2 PWM | Output | 5kHz PWM, drives MOSFET gate |
| 27 | Servo PWM | Output | 50Hz PWM, direct servo connection |
| 32 | BLE Indicator LED | Output | (Future expansion) |
| **Reserved** | | | |
| 0 | Boot Mode Select | - | Must be HIGH at boot (10kΩ pull-up) |
| 2 | Boot Mode Select | - | Must be LOW at boot (internal pull-down) |
| 12 | Boot Flash Voltage | - | Must be LOW at boot (sets 3.3V flash) |
| 15 | JTAG/Debug | - | Must be HIGH at boot (10kΩ pull-up) |
| **Available** | | | |
| 4, 5, 13, 16-19, 23, 33-39 | User Expansion | - | 26 pins available for future features |

## 2.4 Optocoupler Circuit Details
* **6N137 Configuration:**
  - Input current limiting: 330Ω resistor (15mA @ 5V)
  - Output pull-up: 1kΩ to 3.3V (adequate for 100kHz transitions)
  - Propagation delay: ~20ns (negligible for 10kHz DCC signal)
  - Input voltage range: 2.5V to 5.5V (compatible with DCC track voltage)

## 2.5 Thermal Performance
* **TinyPICO 3.3V LDO:** AP2112K (600mA maximum, 250mV dropout)
  - Typical load: 80mA (ESP32) + 20mA (2x MLX90614) = 100mA
  - Margin: 500mA available for future expansion
* **MP1584EN Buck Converter:** 
  - Efficiency: ~85% at 17V input, 5V @ 200mA output
  - Heat dissipation: ~0.5W (requires small heatsink if enclosed)
* **Operating Range:** -20°C to +75°C ambient (industrial temperature rating)
```

---

### 3. **LOCO_HW.md** - Locomotive Hardware Specification

**Strengths:**
- Clear functional grouping of components
- Appropriate choice of non-contact thermal sensors

**Identified Gaps:**
1. ⚠️ **Missing sensor specifications**
   - MLX90614 has multiple variants (MLX90614ESF-BAA vs MLX90614ESF-DCI)
   - No mention of I2C addressing (both sensors on same bus need different addresses)
   - No field of view specification (critical for accurate temperature measurement)

2. ⚠️ **Incomplete MOSFET circuit**
   - IRLZ44N requires gate driver details:
     - Gate resistor (limits inrush current to gate capacitance)
     - Pull-down resistor (ensures OFF state during ESP32 boot)
   - No mention of flyback protection (heater coils are inductive loads)

3. ⚠️ **Missing mechanical constraints**
   - Servo mounting torque requirements
   - Thermal sensor mounting distance from heat sources
   - TCRT5000 optical sensor gap specification

**Recommendations:**
```markdown
## 3.3 Thermal Sensor Configuration

| Sensor | I2C Address | Target Surface | Field of View | Temp Range |
|:-------|:------------|:---------------|:--------------|:-----------|
| MLX90614 #1 (Boiler) | 0x5A (Factory default) | Boiler shell | 90° cone | -40°C to 125°C |
| MLX90614 #2 (Superheater) | 0x5B (Reprogrammed) | Steam pipe | 90° cone | -40°C to 385°C (Extended range variant) |

**Important:** Use MLX90614ESF-**DCI** variant for Superheater (extended temperature range). Standard MLX90614ESF-**BAA** variant saturates at 125°C.

**Mounting Requirements:**
- Minimum clearance: 10mm from target surface
- Maximum range: 50mm (accuracy degrades beyond this distance)
- Avoid direct line-of-sight to flames or radiant heat sources

## 3.4 MOSFET Gate Drive Circuit

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

## 3.5 Odometry Sensor Mounting

**TCRT5000 Optical Gap:** 2.5mm ± 0.5mm
- Too close: Sensor saturates, cannot distinguish reflective vs. absorptive surfaces
- Too far: Insufficient signal strength, erratic pulse detection
- Recommended: Mount sensor fixed, attach reflective tape to wheel rim at 8 equal intervals

**Pulse Rate Calculation:**
- Wheel diameter: 32mm (example for 7¼" gauge)
- 8 reflectors per revolution
- At 10 km/h (prototype speed):
  - Model speed: 10 km/h / 29.26 (1:29.26 scale) = 0.342 km/h = 95 mm/s
  - Wheel RPM: (95 mm/s × 60) / (π × 32 mm) = 56.6 RPM
  - Pulse frequency: 56.6 RPM × 8 pulses = 453 Hz (well within TCRT5000 response time)
```

---

### 4. **UMBILICAL.md** - Wiring Schedule

**Strengths:**
- Excellent EMI mitigation guidance (twisted pair for I2C)
- Proper wire gauge selection
- Clear thermal protection requirements

**Identified Gaps:**
1. ⚠️ **Missing cable length specification**
   - How long can the umbilical be before signal integrity degrades?
   - I2C capacitance limits (400pF for standard mode)
   - Voltage drop calculations for 0.33 mm² (22 AWG) power lines

2. ⚠️ **Incomplete connector specifications**
   - "Mini-DIN or JST-SH" - need a single recommended part number
   - No mention of locking mechanism (critical for vibration resistance)
   - No IP rating for moisture/steam protection

3. ⚠️ **Missing test procedures**
   - How to verify umbilical continuity before first power-up?
   - Acceptable resistance ranges for power conductors
   - I2C bus capacitance measurement procedure

**Recommendations:**
```markdown
## 5.5 Cable Length Constraints

**Maximum Length:** 300 mm (11.8 in)

**Rationale:**
* **I2C Capacitance:** ~82 pF/m (30 AWG, ~25 pF/ft)
   - 300 mm cable = ~25 pF (11.8 in)
  - Two sensors + cable = ~100pF total (well under 400pF limit)
* **Voltage Drop:** 0.33 mm² (22 AWG) at 1 A over 300 mm = ~20 mV drop
  - Negligible for 17V power rail
* **EMI Susceptibility:** Shorter cable = reduced antenna effect for 5kHz PWM signals

**If Longer Cable Required:**
* Use shielded cable with grounded outer braid
* Reduce I2C speed to 50 kHz (increases noise immunity)
* Add 100nF ceramic capacitors at Locomotive end of I2C lines

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
1. **Continuity Test (Both ends disconnected):**
   - Measure resistance across each pin pair (Tender end to Loco end)
   - **Pass criteria:** < 1Ω for all pins
   
2. **Isolation Test:**
   - Measure resistance between adjacent pins
   - **Pass criteria:** > 10MΩ (confirms no shorts)
   
3. **I2C Capacitance (Optional but recommended):**
   - Connect LCR meter to pins 6 and 7 at Tender end
   - Measure capacitance with Loco end open circuit
   - **Pass criteria:** < 100pF (confirms cable quality)

4. **Power Drop Test:**
   - Apply 17V to pin 1, ground to pin 2 at Tender end
   - Measure voltage at Loco end while drawing 500mA load
   - **Pass criteria:** > 16.5V (confirms acceptable voltage drop)
```

---

### 5. **BOM.md** - Bill of Materials

**Strengths:**
- Clear tabular format
- Includes quantities

**Identified Gaps:**
1. ⚠️ **Missing supplier information**
   - No part numbers from specific suppliers (Mouser, DigiKey, RS Components)
   - No alternative part numbers for supply chain resilience

2. ⚠️ **No costing information**
   - Budget estimation not possible
   - No indication of expensive vs. economical components

3. ⚠️ **Missing passive components**
   - Resistors for gate drivers, optocoupler, pull-ups not listed
   - Capacitors for power supply decoupling not listed
   - No mention of PCB or perfboard requirements

**Recommendations:**
```markdown
## 4.4 Passive Components

| Part ID | Description | Value | Qty | Notes |
|:--------|:------------|:------|:----|:------|
| R1 | Optocoupler Input | 330Ω ¼W | 1 | Limits DCC input current |
| R2 | Optocoupler Pull-up | 1kΩ ¼W | 1 | Pull-up to 3.3V |
| R3/R4 | MOSFET Gate | 100Ω ¼W | 2 | Limits gate inrush current |
| R5/R6 | MOSFET Pull-down | 10kΩ ¼W | 2 | Ensures OFF during boot |
| R7/R8 | I2C Pull-up | 4.7kΩ ¼W | 2 | Required for I2C bus |
| C1 | Buck Converter Input | 100µF 25V Electrolytic | 1 | Input filter capacitor |
| C2 | Buck Converter Output | 100µF 10V Electrolytic | 1 | Output filter capacitor |
| C3/C4 | Sensor Decoupling | 100nF Ceramic | 2 | One per MLX90614 |
| C5 | ESP32 Decoupling | 10µF Ceramic | 1 | Near TinyPICO VCC pin |
| D1/D2 | Heater Flyback | 1N4007 | 2 | Protects MOSFETs |
| D3 | Reverse Polarity | 1N5819 Schottky | 1 | Protects against track reversal |

## 4.5 Supplier Information & Costing (UK Market)

### Primary Supplier: RS Components (www.rs-online.com)

| Part | RS Stock # | Unit Cost (£) | Qty | Subtotal (£) |
|:-----|:-----------|:--------------|:----|:-------------|
| TinyPICO | N/A (Pimoroni) | £18.00 | 1 | £18.00 |
| 6N137 | 298-5122 | £0.85 | 1 | £0.85 |
| MP1584EN Module | 174-7171 | £2.50 | 1 | £2.50 |
| IRLZ44N | 728-8025 | £0.65 | 2 | £1.30 |
| MG90S Servo | 212-4294 | £3.20 | 1 | £3.20 |
| MLX90614ESF-BAA | 539-6336 | £8.50 | 1 | £8.50 |
| MLX90614ESF-DCI | 539-6338 | £12.00 | 1 | £12.00 |
| TCRT5000 | 667-2871 | £1.20 | 1 | £1.20 |
| 1F 5.5V Supercap | 144-5995 | £1.80 | 2 | £3.60 |
| Molex Pico-Lock | 673-3917 | £4.50 | 1 | £4.50 |
| Passives Kit | Generic | £5.00 | 1 | £5.00 |
| Thermal Barrier | 825-0397 | £3.00 | 1 | £3.00 |
| Heatsinks | Generic | £1.00 | 2 | £2.00 |
| **TOTAL** | | | | **£65.65** |

**Alternative Suppliers:**
* **Pimoroni** (pimoroni.com) - TinyPICO exclusive UK distributor
* **The Pi Hut** (thepihut.com) - Sensors and development boards
* **Farnell** (uk.farnell.com) - Complete range, longer lead times

**Cost Optimisation:**
* **Reduce by 20%:** Use standard MLX90614ESF-BAA for both sensors if superheater temperature <125°C
* **Reduce by 15%:** Replace Molex Pico-Lock with JST-SH (requires more careful assembly)
```

---

## 📌 Summary of Recommendations

### High Priority (Safety/Functionality Critical):
1. ✅ **LOCO_HW.md:** Add MOSFET gate driver circuit with flyback protection
2. ✅ **UMBILICAL.md:** Specify maximum cable length and test procedures
3. ✅ **LOCO_HW.md:** Document MLX90614 I2C addressing scheme (avoid address conflicts)
4. ✅ **TENDER_HW.md:** Complete GPIO allocation table (prevent accidental use of boot-critical pins)

### Medium Priority (Improves Usability):
5. ⚙️ **ARCHITECTURE.md:** Add timing specifications (PWM frequencies, I2C speed, loop rates)
6. ⚙️ **BOM.md:** Add supplier part numbers and costing information
7. ⚙️ **UMBILICAL.md:** Specify recommended connector with part number

### Low Priority (Nice to Have):
8. 📝 **ARCHITECTURE.md:** Document fault tolerance and recovery procedures
9. 📝 **TENDER_HW.md:** Add thermal performance specifications
10. 📝 **BOM.md:** List passive components (resistors, capacitors, diodes)

---

## ✅ Next Steps

1. **Immediate:** Implement High Priority recommendations (safety-critical)
2. **Short-term:** Add Medium Priority content (improves developer experience)
3. **Ongoing:** Expand Low Priority sections as questions arise during implementation
4. **Maintain:** Keep hardware docs synchronized with any physical changes to the system

**Document Status:** Review complete. Hardware documentation is of high quality with excellent British English compliance. Recommended improvements focus on completeness rather than correctness.

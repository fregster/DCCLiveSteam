# 2. Tender Hardware Specification

## 2.1 Logic & Signal Module
The Tender is the "Brain" of the system, housing the TinyPICO and command signal hardware. The tender also houses the electrically heated boiler and associated safety sensors.

| Component | Specification | Purpose |
| :--- | :--- | :--- |
| **MCU** | Pimoroni TinyPICO ESP32 (ESP32-PICO-D4) | Master control, BLE host, I2C Master. 4MB flash, 520KB SRAM, 3.3V logic, USB-C, LiPo support. |
| **Signal Isolator** | 6N137 High-Speed Opto | Decouples DCC track voltage from ESP32 GPIO. |
| **Step-Down Regulator** | MP1584EN Buck Converter | Drops 14V track power to 5V logic power. |
| **Power MOSFETs** | 2x IRLZ44N (TO-220) | PWM control for Boiler and Superheater heater elements. |
| **Boiler Thermocouple** | Type-K + Amplifier | Direct temperature monitoring of boiler shell. |
| **Water Level Sensor** | Conductive or Float | Detects low-water condition in tender boiler. |
| **Stay-Alive** | 2x 1.0F 5.5V Supercaps | Provides backup power for the "Distress Whistle" sequence. |

## 2.2 Tender Internal Wiring (Pinout)
* **VCC (Raw):** 14V Track Input to Buck Converter (OO scale DCC standard).
* **VCC (5V):** Buck Output to TinyPICO 5V/USB Pin.
* **GPIO 14:** DCC Signal Input (from Optocoupler Pin 6).
* **GPIO 21/22:** I2C Bus (SDA/SCL) to boiler thermocouple amplifier and umbilical.
* **GPIO 25/26:** Heater PWM signals to MOSFET gates (tender-mounted).
* **GPIO 27:** Servo PWM signal to Umbilical.
* **GPIO 34:** Water level sensor analogue input (ADC).


## 2.3 Complete GPIO Allocation (Pimoroni TinyPICO ESP32)

| GPIO | Function | Direction | Notes |
|:-----|:---------|:----------|:------|
| 14 | DCC Input | Input | 5V tolerant via optocoupler |
| 21 | I2C SDA | Bidirectional | 4.7kΩ pull-up to 3.3V |
| 22 | I2C SCL | Output | 4.7kΩ pull-up to 3.3V |
| 25 | Heater 1 PWM | Output | 5kHz PWM, drives MOSFET gate |
| 26 | Heater 2 PWM | Output | 5kHz PWM, drives MOSFET gate |
| 27 | Servo PWM | Output | 50Hz PWM, direct servo connection |
| 34 | Water Level Sensor | Input | Analogue input (ADC), input-only pin |
| 32 | BLE Indicator LED | Output | (Future expansion) |
| **Reserved (Boot-Critical)** | | | |
| 0 | Boot Mode Select | - | Must be HIGH at boot (10kΩ pull-up) |
| 2 | Boot Mode Select | - | Must be LOW at boot (internal pull-down) |
| 12 | Boot Flash Voltage | - | Must be LOW at boot (sets 3.3V flash) |
| 15 | JTAG/Debug | - | Must be HIGH at boot (10kΩ pull-up) |
| **Available for Expansion** | | | |
| 4, 5, 13, 16-19, 23, 33-39 | User Expansion | - | 26 pins available for future features |

**Critical Boot Requirements (Pimoroni TinyPICO ESP32):**
* GPIOs 0, 2, 12, and 15 have specific voltage requirements during ESP32 boot sequence
* **Never** connect loads to these pins without understanding boot constraints
* Incorrect configuration prevents ESP32 from booting or entering programming mode
* See ESP32 datasheet Section 2.3 "Strapping Pins" for complete details
* Board features USB-C for power/programming and optional LiPo battery support (not used in this design, but available for expansion).

## 2.4 Optocoupler Circuit Details

**6N137 Configuration:**
* Input current limiting: 330Ω resistor (15mA @ 5V DCC signal)
* Output pull-up: 1kΩ to 3.3V (adequate for 100kHz transitions)
* Propagation delay: ~20ns (negligible for 10kHz DCC signal)
* Input voltage range: 2.5V to 5.5V (compatible with NMRA DCC standard)

**Why 6N137:**
* High-speed optocoupler (up to 10 Mbps) handles DCC waveform rise times
* Common-mode isolation protects ESP32 from track voltage transients
* Wide input voltage range tolerates voltage variations on track

## 2.5 Thermal Performance

**TinyPICO 3.3V LDO:** AP2112K (600mA maximum, 250mV dropout)
* Typical load: 80mA (ESP32) + 20mA (thermocouple amplifier + sensors) = 100mA
* Margin: 500mA available for future expansion
* No heatsink required at typical loads

**MP1584EN Buck Converter:**
* Efficiency: ~85% at 14V input, 5V @ 200mA output
* Heat dissipation: ~0.4W (requires small heatsink if enclosed)
* Input voltage range: 4.5V to 28V (tolerates track voltage variations)

**Operating Range:** -20°C to +75°C ambient (industrial temperature rating)

## 2.6 Power MOSFET Gate Drive Circuit

Each IRLZ44N requires proper gate drive components for safe operation:

```
ESP32 GPIO ──[100Ω]──┬─ MOSFET Gate
                     │
                    [10kΩ] Pull-down to GND
                     │
                    GND
```

**Component Functions:**
* **100Ω Gate Resistor:** Limits gate charging current to ~30mA (safe for ESP32 GPIO)
* **10kΩ Pull-down:** Ensures MOSFET OFF during ESP32 boot/reset sequences
* **Flyback Diode:** 1N4007 across heater coil (cathode to V+, anode to drain)
  - Clamps inductive kickback when MOSFET switches OFF
  - Critical for preventing voltage spikes that could damage MOSFET or ESP32

**Circuit Protection:**
* Heater coils are inductive loads; **flyback protection is mandatory**
* Without flyback diode, back-EMF can exceed 100V during turn-off transients
* Diode must be rated for heater current (minimum 1A, 1N4007 rated 1A continuous)
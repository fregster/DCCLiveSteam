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
# 4. Bill of Materials

## 4.1 Semiconductor & Modules
| Part ID | Description | Model | Qty |
| :--- | :--- | :--- | :--- |
| MCU-1 | Microcontroller | TinyPICO (ESP32) | 1 |
| OPTO-1 | Optocoupler | 6N137 | 1 |
| PWR-1 | Buck Converter | MP1584EN | 1 |
| FET-1/2 | MOSFET | IRLZ44N (TO-220) | 2 |

## 4.2 Sensors & Actuators
| Part ID | Description | Model | Qty |
| :--- | :--- | :--- | :--- |
| SRV-1 | Metal Gear Servo | MG90S | 1 |
| SEN-1 | Thermocouple | Type-K | 2 |
| SEN-2 | Thermocouple Amplifier | I2C/SPI Module | 2 |
| SEN-3 | Pressure Sensor | 0–200 PSI Transducer | 1 |
| SEN-4 | Water Level Sensor | Conductive or Float | 1 |
| SEN-5 | IR Speed Sensor | TCRT5000 | 1 |
| CAP-1 | Supercapacitor | 1.0F 5.5V | 2 |

## 4.3 Connectors & Misc
| Part ID | Description | Detail | Qty |
| :--- | :--- | :--- | :--- |
| CONN-1 | 8-Pin Umbilical | JST-SH or Micro-DIN | 1 |
| ISO-1 | Thermal Barrier | Ceramic Fiber Paper | 1 |
| HS-1 | MOSFET Heatsink | Small aluminum fin | 2 |
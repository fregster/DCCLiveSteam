# Deployment Guide: TinyPICO Installation

This guide provides step-by-step instructions for deploying the live steam locomotive controller firmware to a TinyPICO ESP32 board.

---

## Prerequisites

### Hardware Requirements
- **TinyPICO** ESP32 development board
- USB-C cable for programming
- Live steam locomotive with:
  - Servo-controlled regulator
  - NTC thermistors (3x): boiler, superheater, logic bay
  - Pressure transducer (0.5-4.5V analog output)
  - Optical encoder (optional, for velocity feedback)
  - PWM-controlled heating elements (boiler + superheater)
  - DCC track signal input

### Software Requirements
- **Python 3.8+** installed on development machine
- **ampy** (Adafruit MicroPython Tool) for file transfer
- **esptool** for flashing MicroPython firmware
- **MicroPython v1.20+** firmware for ESP32

---

## Step 1: Install MicroPython on TinyPICO

### 1.1 Install esptool
```bash
pip install esptool
```

### 1.2 Download MicroPython Firmware
Download the latest ESP32 firmware from:
https://micropython.org/download/esp32/

**Recommended:** `esp32-20231005-v1.21.0.bin` (or newer)

### 1.3 Erase Flash
```bash
esptool.py --port /dev/ttyUSB0 erase_flash
```

**Note:** Replace `/dev/ttyUSB0` with your serial port:
- **macOS:** `/dev/tty.usbserial-*` or `/dev/cu.usbserial-*`
- **Windows:** `COM3`, `COM4`, etc.
- **Linux:** `/dev/ttyUSB0` or `/dev/ttyACM0`

### 1.4 Flash MicroPython
```bash
esptool.py --chip esp32 --port /dev/ttyUSB0 write_flash -z 0x1000 esp32-20231005-v1.21.0.bin
```

### 1.5 Verify Installation
```bash
screen /dev/ttyUSB0 115200
```

You should see the MicroPython REPL prompt:
```python
>>>
```

Press `Ctrl+D` to reboot. Exit screen with `Ctrl+A` then `K`.

---

## Step 2: Install ampy for File Transfer

### 2.1 Install ampy
```bash
pip install adafruit-ampy
```

### 2.2 Test Connection
```bash
ampy --port /dev/ttyUSB0 ls
```

Should return empty list on fresh MicroPython install.

---

## Step 3: Deploy Application Files

### 3.1 Upload `app/` Directory
Upload all Python modules to the TinyPICO:

```bash
# Navigate to project root
cd /path/to/DCCLiveSteam

# Upload app package
ampy --port /dev/ttyUSB0 put app

# Verify upload
ampy --port /dev/ttyUSB0 ls /app
```

Expected output:
```
/app/__init__.py
/app/actuators.py
/app/ble_advertising.py
/app/ble_uart.py
/app/config.py
/app/dcc_decoder.py
/app/main.py
/app/physics.py
/app/safety.py
/app/sensors.py
```

### 3.2 Create `boot.py` (Optional)
Create a `boot.py` file that runs on every boot:

```python
# boot.py - TinyPICO boot configuration
import gc
import machine

# Disable WiFi to save power (BLE only)
import network
wlan = network.WLAN(network.STA_IF)
wlan.active(False)

# Enable garbage collection
gc.enable()
gc.collect()

print("TinyPICO Boot Complete")
print("Free Memory:", gc.mem_free(), "bytes")
```

Upload `boot.py`:
```bash
ampy --port /dev/ttyUSB0 put boot.py
```

### 3.3 Create `main.py` Launcher
Create a `main.py` file in the root directory:

```python
# main.py - Auto-run on boot
from app.main import run

if __name__ == "__main__":
    run()
```

Upload `main.py`:
```bash
ampy --port /dev/ttyUSB0 put main.py
```

---

## Step 4: Configure CVs (Initial Setup)

### 4.1 Create `config.json`
On first boot, the system will auto-create `config.json` with factory defaults. To customize before deployment, create a local `config.json`:

```json
{
  "1": 3,
  "29": 6,
  "30": 1,
  "31": 0,
  "33": 35.0,
  "37": 1325,
  "38": 12,
  "39": 203,
  "40": 76,
  "41": 75,
  "42": 110,
  "43": 250,
  "44": 20,
  "45": 8,
  "46": 77,
  "47": 128,
  "48": 5,
  "49": 1000
}
```

**Key CVs to customize:**
- **CV1:** DCC address (default: 3)
- **CV46:** Servo neutral position PWM duty cycle (calibrate per locomotive)
- **CV47:** Servo maximum position PWM duty cycle (calibrate per locomotive)
- **CV37:** Wheel radius in 0.01mm (default: 1325 = 13.25mm)
- **CV40:** Scale ratio (76 for OO, 87 for HO, 160 for N)

Upload `config.json`:
```bash
ampy --port /dev/ttyUSB0 put config.json
```

---

## Step 5: Test Deployment

### 5.1 Connect to Serial Console
```bash
screen /dev/ttyUSB0 115200
```

### 5.2 Reboot TinyPICO
Press the reset button or:
```python
>>> import machine
>>> machine.reset()
```

### 5.3 Verify Boot Sequence
You should see:
```
TinyPICO Boot Complete
Free Memory: 100000 bytes
LOCOMOTIVE CONTROLLER BOOTING...
System Ready. Address: 3
```

### 5.4 Monitor Telemetry Output
Every 50 seconds, you should see status updates:
```
SPD:0.0 PSI:0.0 T:25/25/25 SRV:77
```

Format: `SPD:<velocity_cms> PSI:<pressure> T:<boiler>/<super>/<logic> SRV:<servo_pwm>`

---

## Step 6: Hardware Wiring

### Pin Assignments (TinyPICO)

| Component | TinyPICO Pin | Type | Description |
|-----------|--------------|------|-------------|
| Boiler Heater | GPIO 25 | PWM Output | 5kHz PWM for heating element |
| Superheater | GPIO 26 | PWM Output | 5kHz PWM for secondary heater |
| Servo | GPIO 27 | PWM Output | 50Hz PWM for regulator servo |
| Track Voltage | GPIO 33 | ADC Input | Rectified DCC voltage (5:1 divider) |
| DCC Signal | GPIO 14 | Digital Input | Raw DCC signal (interrupt-driven) |
| Encoder | GPIO 32 | Digital Input | Optical encoder (interrupt on falling edge) |
| Pressure | GPIO 34 | ADC Input | Pressure transducer (0.5-4.5V) |
| Logic Temp | GPIO 35 | ADC Input | NTC thermistor (10kΩ @ 25°C) |

### Wiring Notes
1. **DCC Signal:** Use optoisolator (6N137 or similar) to isolate DCC track from ESP32
2. **ADC Inputs:** All analog inputs are 0-3.3V max. Use voltage dividers for higher voltages.
3. **Heater PWM:** Use MOSFET driver circuit (IRLZ44N or similar) rated for heating element current.
4. **Servo:** Connect to 5V servo power supply (NOT TinyPICO 3.3V rail). Share GND.
5. **Track Voltage:** Use 5:1 voltage divider (e.g., 40kΩ + 10kΩ resistors) to scale 18V DCC to 3.6V ADC input.

### Power Supply Requirements
- **TinyPICO:** 5V USB or track power via regulator
- **Servo:** 5-6V @ 500mA peak
- **Heaters:** 3-12V @ 1-2A (depends on boiler size)
- **Stay-Alive Capacitor:** 1F @ 5.5V (optional, recommended for power loss resilience)

---

## Step 7: Calibration

### 7.1 Servo Calibration
1. Connect to serial console
2. Import calibration functions:
   ```python
   >>> from app.config import load_cvs, save_cvs
   >>> from app.actuators import MechanicalMapper
   >>> cv = load_cvs()
   ```

3. Find neutral position (regulator fully closed):
   ```python
   >>> mapper = MechanicalMapper(cv)
   >>> mapper.servo.duty(77)  # Start with default
   # Adjust until regulator is fully closed
   >>> mapper.servo.duty(80)
   >>> cv[46] = 80  # Update CV46
   ```

4. Find maximum position (regulator fully open):
   ```python
   >>> mapper.servo.duty(128)  # Start with default
   # Adjust until regulator is at 90° open
   >>> mapper.servo.duty(125)
   >>> cv[47] = 125  # Update CV47
   ```

5. Save calibration:
   ```python
   >>> save_cvs(cv)
   ```

### 7.2 Pressure Calibration
1. Fill boiler and heat to operating pressure
2. Compare BLE telemetry pressure reading to physical gauge
3. Adjust pressure transducer scaling if needed (requires code modification in `sensors.py`)

### 7.3 Temperature Calibration
Thermistors are pre-calibrated using Steinhart-Hart equation. If readings are inaccurate:
1. Measure actual temperatures with external thermometer
2. Adjust NTC parameters in `sensors.py` (R0, B-constant)

---

## Step 8: BLE Telemetry Setup

### 8.1 Connect via BLE
1. Use BLE terminal app (nRF Connect, Serial Bluetooth Terminal, etc.)
2. Scan for device named "Locomotive" (or custom name from `ble_uart.py`)
3. Connect to Nordic UART Service (UUID: 6E400001-B5A3-F393-E0A9-E50E24DCCA9E)

### 8.2 Telemetry Format
Every 1 second, you'll receive:
```
V:12.5 P:35.2 B:95.0 S:210.0 L:45.0 SRV:102
```

Format:
- `V`: Velocity (cm/s)
- `P`: Pressure (PSI)
- `B`: Boiler temperature (°C)
- `S`: Superheater temperature (°C)
- `L`: Logic bay temperature (°C)
- `SRV`: Servo PWM duty cycle

---

## Troubleshooting

### Issue: TinyPICO won't boot after deployment
**Solution:**
1. Connect to serial console
2. Check for Python syntax errors
3. Remove `main.py` to prevent auto-start:
   ```bash
   ampy --port /dev/ttyUSB0 rm main.py
   ```
4. Manually import to debug:
   ```python
   >>> from app.main import run
   >>> run()  # See error messages
   ```

### Issue: "MemoryError" during operation
**Solution:**
1. Reduce `EVENT_BUFFER_SIZE` in `config.py` (default: 20)
2. Lower `GC_THRESHOLD` in `config.py` (default: 61440 bytes)
3. Disable BLE telemetry (saves ~15KB RAM)

### Issue: Servo jitter or erratic movement
**Solution:**
1. Check servo power supply (needs clean 5-6V @ 500mA)
2. Increase `CV49` (travel time) for smoother motion
3. Verify `CV46` and `CV47` calibration
4. Check for mechanical binding in regulator linkage

### Issue: Temperature readings show 999.9°C
**Solution:**
1. Verify NTC thermistor connections (not open circuit)
2. Check ADC voltage is within 0-3.3V range
3. Replace faulty thermistor (10kΩ @ 25°C NTC required)

### Issue: DCC commands not responding
**Solution:**
1. Verify DCC signal wiring (use optoisolator)
2. Check DCC address (CV1) matches command station
3. Increase DCC timeout (`CV44`) if packet loss suspected
4. Verify track voltage > 12V (check with multimeter)

---

## Recovery Procedures

### Full Flash Erase and Reinstall
If system is unrecoverable:
1. Erase flash: `esptool.py --port /dev/ttyUSB0 erase_flash`
2. Re-flash MicroPython (see Step 1.4)
3. Re-deploy all files (Steps 3.1-3.3)
4. Recalibrate (Step 7)

### Factory Reset (Preserve Code)
To reset CVs to factory defaults:
1. Connect to serial console
2. Delete config:
   ```python
   >>> import os
   >>> os.remove('config.json')
   >>> import machine
   >>> machine.reset()
   ```
3. System will recreate `config.json` with defaults on next boot

### Extract Black Box Logs
After emergency shutdown:
1. Connect to serial console
2. Retrieve logs:
   ```python
   >>> import json
   >>> with open('error_log.json', 'r') as f:
   ...     logs = json.load(f)
   >>> print(logs)
   ```
3. Download to PC:
   ```bash
   ampy --port /dev/ttyUSB0 get error_log.json
   ```

---

## Post-Deployment Checklist

- [ ] Servo moves smoothly from neutral to max position
- [ ] Temperature readings show ambient (~25°C) when cold
- [ ] Pressure reading shows 0 PSI when boiler cold
- [ ] DCC address matches command station setting
- [ ] BLE telemetry connects and updates every 1 second
- [ ] Watchdog triggers on simulated thermal fault (test with hot air gun)
- [ ] E-STOP command (F12) closes regulator instantly
- [ ] Distress whistle sounds during emergency shutdown (if enabled via CV30)
- [ ] Serial console shows "SPD:X PSI:Y T:Z" updates every 50 seconds
- [ ] System survives power cycle without corruption

---

## See Also

- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Detailed fault diagnosis
- [CV.md](CV.md) - Complete CV reference for tuning
- [FUNCTIONS.md](FUNCTIONS.md) - DCC function mapping and API reference
- [capabilities.md](capabilities.md) - System features and limitations

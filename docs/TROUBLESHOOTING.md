### Speed/Throttle Not Responding as Expected

**Symptom:** Locomotive does not accelerate smoothly, or throttle does not match DCC speed command.

**Possible Cause:** CV52 (Speed Control Mode) is set incorrectly for your desired behaviour.

**Solution:**
- Set CV52 = 1 for cruise control (automatic speed regulation).
- Set CV52 = 0 for direct throttle (manual regulator control).

Refer to CV.md for details on setting CV52.
# Troubleshooting Guide

This guide helps diagnose and resolve common issues with the live steam locomotive controller.

---

## Quick Diagnostic Steps

When experiencing issues:
1. **Check Serial Console** - Connect via USB and check for error messages
2. **Check BLE Telemetry** - Verify sensor readings are realistic
3. **Check Power Supply** - Ensure clean 5V to TinyPICO, 5-6V to servo
4. **Check Wiring** - Verify all sensor connections are secure
5. **Check Memory** - Run `gc.mem_free()` in REPL to check available RAM

---

## Boot & Initialisation Issues

### System Won't Boot / REPL Not Responding

**Symptoms:**
- No serial output on boot
- REPL not responding to commands
- TinyPICO LED not blinking

**Possible Causes:**
1. **Corrupted MicroPython firmware**
2. **Faulty USB cable or port**
3. **Brownout from insufficient power**

**Solutions:**
1. Try different USB cable and port
2. Re-flash MicroPython firmware:
   ```bash
   esptool.py --port /dev/ttyUSB0 erase_flash
   esptool.py --chip esp32 --port /dev/ttyUSB0 write_flash -z 0x1000 esp32-*.bin
   ```
3. Disconnect all external peripherals (servo, sensors) and test with bare TinyPICO
4. Check 5V power supply can deliver 500mA minimum

---

### "MemoryError" or "OSError: [Errno 28] No space"

**Symptoms:**
- System crashes with `MemoryError` during operation
- Cannot save config.json
- Flash write errors

**Possible Causes:**
1. **Insufficient RAM** - Heap fragmentation or memory leak
2. **Flash storage full** - Too many error logs
3. **Large event buffer** - Circular buffer too large

**Solutions:**

**For RAM issues:**
1. Force garbage collection in REPL:
   ```python
   >>> import gc
   >>> gc.collect()
   >>> print(gc.mem_free())  # Should show > 60000 bytes
   ```

2. Reduce `GC_THRESHOLD` in `app/config.py`:
   ```python
   GC_THRESHOLD = 80000  # Trigger GC more aggressively (default: 61440)
   ```

3. Reduce `EVENT_BUFFER_SIZE` in `app/config.py`:
   ```python
   EVENT_BUFFER_SIZE = 10  # Reduce from default 20
   ```

4. Disable BLE telemetry to save ~15KB RAM:
   ```python
   # In app/main.py Locomotive.__init__()
   # Comment out: self.ble = BLE_UART()
   ```

**For flash storage issues:**
1. Check available space:
   ```python
   >>> import os
   >>> os.statvfs('/')
   # Returns (bsize, frsize, blocks, bfree, bavail, files, ffree, favail, flag, namemax)
   >>> info = os.statvfs('/')
   >>> free_kb = (info[0] * info[3]) / 1024
   >>> print(f"Free: {free_kb} KB")
   ```

2. Delete old error logs:
   ```python
   >>> os.remove('error_log.json')
   ```

3. List and remove unused files:
   ```python
   >>> os.listdir('/')
   ```

---

### Import Errors / Module Not Found

**Symptoms:**
- `ImportError: no module named 'app.X'`
- System crashes on boot with import error

**Possible Causes:**
1. **Incomplete file upload** - Missing files from `app/` directory
2. **Incorrect directory structure** - Files not in `app/` package
3. **Typo in import statement**

**Solutions:**
1. Verify all files uploaded:
   ```bash
   ampy --port /dev/ttyUSB0 ls /app
   ```

2. Re-upload missing files:
   ```bash
   ampy --port /dev/ttyUSB0 put app
   ```

3. Check `app/__init__.py` exists (required for Python package)

4. Verify imports in REPL:
   ```python
   >>> from app.main import run  # Should work without error
   ```

---

## Sensor Issues

### Temperature Readings Show 999.9°C

**Symptoms:**
- BLE telemetry shows `B:999.9` or `S:999.9` or `L:999.9`
- Serial console shows extreme temperature values
- Watchdog triggers thermal shutdown immediately

**Possible Causes:**
1. **Open circuit** - Thermistor not connected or broken wire
2. **ADC reading zero** - Short circuit or faulty ADC pin
3. **Wrong thermistor type** - Not 10kΩ @ 25°C NTC

**Solutions:**
1. Measure thermistor resistance with multimeter:
   - Should be ~10kΩ at room temperature (25°C)
   - Resistance decreases as temperature increases
   
2. Check ADC voltage at TinyPICO pin:
   ```python
   >>> from machine import ADC
   >>> adc = ADC(Pin(25))  # Boiler thermistor
   >>> adc.read()          # Should be ~2048 at 25°C
   ```

3. Verify wiring:
   - Thermistor in voltage divider: VCC → 10kΩ → ADC pin → Thermistor → GND
   - Check for loose connections or damaged wires

4. Replace thermistor if resistance measurement is incorrect

---

### Pressure Reading is Stuck at 0.0 or 100.0

**Symptoms:**
- Pressure never changes from 0.0 kPa (0.0 PSI)
- Pressure reading maxed at 690 kPa (100.0 PSI)
- PID controller doesn't activate heaters

**Possible Causes:**
1. **Sensor disconnected** - Open circuit or bad connection
2. **Incorrect voltage range** - Sensor not 0.5-4.5V type
3. **ADC pin damaged** - Pin reading constant voltage

**Solutions:**
1. Check sensor output voltage with multimeter:
   - At 0 kPa (0 PSI): should be 0.5V
   - At 345 kPa (50 PSI): should be 2.5V
   - At 690 kPa (100 PSI): should be 4.5V

2. Test ADC reading in REPL:
   ```python
   >>> from machine import ADC, Pin
   >>> from app.config import PIN_PRESSURE
   >>> adc = ADC(Pin(PIN_PRESSURE))
   >>> adc.read()  # Should be 620-2790 for 0–690 kPa (0–100 PSI) range
   ```

3. Verify pressure transducer type:
   - Must be 0.5-4.5V analog output
   - NOT 4-20mA current loop type (requires different circuit)

4. Check power supply to sensor (typically 5V)

---

### Encoder Not Counting / Velocity Always 0.0

**Symptoms:**
- BLE telemetry shows `V:0.0` even when locomotive moving
- Encoder count doesn't increment
- Speed calculations incorrect

**Possible Causes:**
1. **Encoder not connected** - Missing wire or bad connection
2. **Wrong encoder type** - Not optical or incompatible output
3. **ISR not triggering** - Noise or incorrect trigger edge
4. **Wheel not rotating** - Mechanical binding

**Solutions:**
1. Check encoder output in REPL:
   ```python
   >>> from app.sensors import SensorSuite
   >>> sensors = SensorSuite()
   >>> sensors.update_encoder()  # Returns count
   # Manually rotate wheel and check count increments
   ```

2. Verify encoder signal:
   - Should be 0-3.3V digital pulses
   - Use oscilloscope or logic analyser to view signal
   - Check for noise or ringing

3. Test interrupt trigger:
   ```python
   >>> from machine import Pin
   >>> from app.config import PIN_ENCODER
   >>> pin = Pin(PIN_ENCODER, Pin.IN)
   >>> pin.value()  # Should toggle 0/1 as wheel rotates
   ```

4. Verify encoder segments (CV38) matches physical encoder disc

---

## DCC Signal Issues

### No Response to DCC Commands

**Symptoms:**
- Locomotive doesn't respond to throttle changes
- BLE telemetry shows speed always 0
- `dcc.is_active()` returns False

**Possible Causes:**
1. **Wrong DCC address** - CV1 doesn't match command station
2. **DCC signal not reaching decoder** - Wiring or optoisolator issue
3. **Incorrect packet format** - Command station sending wrong format
4. **ISR not triggering** - GPIO14 not receiving interrupts

**Solutions:**
1. Verify DCC address:
   ```python
   >>> from app.config import load_cvs
   >>> cv = load_cvs()
   >>> print("Address:", cv[1])  # Should match command station
   ```

2. Test DCC signal at TinyPICO pin:
   - Use oscilloscope to view signal on GPIO14
   - Should see square wave at ~8kHz with varying pulse widths
   - Voltage should be 0-3.3V (after optoisolator)

3. Check DCC timing constants in `app/config.py`:
   ```python
   DCC_ONE_MIN = 52   # µs
   DCC_ONE_MAX = 64
   DCC_ZERO_MIN = 95
   DCC_ZERO_MAX = 119
   ```

4. Test with broadcast address (0):
   ```python
   >>> cv[1] = 0  # Broadcast address
   >>> from app.config import save_cvs
   >>> save_cvs(cv)
   >>> # Reboot and test
   ```

5. Increase DCC timeout if signal is intermittent:
   ```python
   >>> cv[44] = 50  # 5000ms timeout (default: 20 = 2000ms)
   >>> save_cvs(cv)
   ```

---

### DCC Signal Triggers Watchdog Timeout

**Symptoms:**
- System shuts down with "DCC_LOST" error
- Works briefly then stops
- Watchdog timeout too aggressive

**Possible Causes:**
1. **Dirty track** - Intermittent contact
2. **DCC timeout too short** - CV44 too low
3. **Packet loss** - RF interference or signal degradation

**Solutions:**
1. Clean track with track cleaning car or alcohol wipe

2. Increase DCC timeout (CV44):
   ```python
   >>> cv[44] = 50  # 5000ms (default: 20 = 2000ms)
   >>> save_cvs(cv)
   ```

3. Check track voltage:
   - Should be 12-18V RMS (DCC standard)
   - Use multimeter in AC mode
   - Verify voltage at locomotive pickup wheels

4. Add stay-alive capacitor (1F @ 5.5V) to bridge momentary power loss

---

## Servo & Mechanical Issues

### Servo Jittering or Oscillating

**Symptoms:**
- Servo buzzes or vibrates at idle
- Regulator moves erratically
- Excessive servo current draw

**Possible Causes:**
1. **Insufficient power** - Servo power supply too weak
2. **Jitter sleep not working** - Servo not entering sleep mode
3. **Mechanical binding** - Regulator linkage sticking
4. **Incorrect PWM frequency** - Not 50Hz

**Solutions:**
1. Verify servo power supply:
   - Must provide 5-6V @ 500mA peak
   - Use capacitor (100-470µF) across servo power pins
   - Check voltage doesn't drop below 4.5V under load

2. Check jitter sleep in code (`app/actuators.py`):
   ```python
   # After 2 seconds idle, servo.duty(0) should be called
   # Monitor serial console for servo state changes
   ```

3. Manually test servo position:
   ```python
   >>> from app.actuators import MechanicalMapper
   >>> from app.config import load_cvs
   >>> cv = load_cvs()
   >>> mapper = MechanicalMapper(cv)
   >>> mapper.servo.duty(77)  # Neutral
   >>> mapper.servo.duty(0)   # Power off (jitter sleep)
   ```

4. Lubricate regulator linkage and check for mechanical interference

---

### Servo Doesn't Move or Moves to Wrong Position

**Symptoms:**
- Servo doesn't respond to commands
- Regulator position doesn't match throttle
- Servo moves but not to correct angle

**Possible Causes:**
1. **Calibration incorrect** - CV46/CV47 not set correctly
2. **Slew rate too slow** - CV49 too large
3. **Servo power failure** - Not receiving 5-6V
4. **PWM signal not reaching servo** - Wiring or GPIO issue

**Solutions:**
1. Recalibrate servo endpoints (CV46, CV47):
   ```python
   >>> from app.actuators import MechanicalMapper
   >>> from app.config import load_cvs, save_cvs
   >>> cv = load_cvs()
   >>> mapper = MechanicalMapper(cv)
   
   # Test neutral position
   >>> mapper.servo.duty(77)  # Adjust until regulator fully closed
   >>> cv[46] = 77  # Update CV
   
   # Test max position
   >>> mapper.servo.duty(128)  # Adjust until regulator fully open (90°)
   >>> cv[47] = 128
   
   >>> save_cvs(cv)
   ```

2. Reduce slew rate for faster response:
   ```python
   >>> cv[49] = 500  # 500ms for 0-100% (default: 1000ms)
   >>> save_cvs(cv)
   ```

3. Test servo directly:
   ```python
   >>> from machine import Pin, PWM
   >>> servo = PWM(Pin(27), freq=50)
   >>> servo.duty(102)  # Mid-position (should be 90° from extremes)
   ```

4. Check servo wiring:
   - Signal wire to GPIO27
   - Power (red) to 5-6V supply
   - Ground (black/brown) to TinyPICO GND

---

### Emergency Shutdown Triggers Unexpectedly

**Symptoms:**
- System enters emergency shutdown during normal operation
- "DRY_BOIL", "SUPER_HOT", or "LOGIC_HOT" error
- Distress whistle activates without cause

**Possible Causes:**
1. **Thermal thresholds too low** - CV41/42/43 too conservative
2. **Faulty temperature sensor** - Reporting incorrect high temperature
3. **Actual thermal fault** - Real overheating condition

**Solutions:**
1. Check actual temperatures vs telemetry:
   - Use external thermometer to verify sensor readings
   - Compare BLE telemetry to physical measurement

2. Review thermal limits (CVs 41-43):
   ```python
   >>> from app.config import load_cvs
   >>> cv = load_cvs()
   >>> print("Logic Limit:", cv[41], "°C")   # Default: 75°C
   >>> print("Boiler Limit:", cv[42], "°C")  # Default: 110°C
   >>> print("Super Limit:", cv[43], "°C")   # Default: 250°C
   ```

3. Increase thermal limits if sensors are accurate:
   ```python
   >>> cv[41] = 80  # Logic (ESP32 max is 85°C)
   >>> cv[42] = 115 # Boiler (conservative for scale)
   >>> cv[43] = 260 # Superheater (gasket limit is 260°C)
   >>> save_cvs(cv)
   ```

4. Check for real thermal issues:
   - Insufficient water in boiler (dry boil)
   - Blocked superheater tubes
   - Inadequate ventilation in logic bay
   - Excessive ambient temperature

---

## BLE Telemetry Issues

### Cannot Connect to BLE Device

**Symptoms:**
- Device not visible in BLE scan
- Connection attempts fail
- "Locomotive" device not appearing

**Possible Causes:**
1. **BLE not initialised** - Code error or disabled
2. **BLE stack crashed** - Memory corruption
3. **Wrong device name** - Looking for incorrect name
4. **Out of range** - BLE distance limited to ~10m

**Solutions:**
1. Verify BLE is active in REPL:
   ```python
   >>> from app.ble_uart import BLE_UART
   >>> ble = BLE_UART(name="TestLoco")
   >>> ble.advertise()
   ```

2. Check BLE device name:
   ```python
   # Default name is "Locomotive"
   # Can customize in app/main.py Locomotive.__init__()
   ```

3. Restart Bluetooth on phone/tablet

4. Use dedicated BLE scanner app (nRF Connect) to verify device is advertising

5. Reboot TinyPICO:
   ```python
   >>> import machine
   >>> machine.reset()
   ```

---

### BLE Connected But No Telemetry Data

**Symptoms:**
- BLE connection established
- No data received in terminal app
- Telemetry queue not sending

**Possible Causes:**
1. **Wrong BLE service** - Not connected to Nordic UART Service
2. **Notifications not enabled** - Characteristic not configured
3. **Telemetry not being queued** - Main loop not calling `send_telemetry()`

**Solutions:**
1. Verify Nordic UART Service UUID:
   - Service: `6E400001-B5A3-F393-E0A9-E50E24DCCA9E`
   - TX Characteristic: `6E400003-B5A3-F393-E0A9-E50E24DCCA9E` (enable notifications)

2. Enable notifications on TX characteristic in BLE app

3. Check telemetry is being sent:
   ```python
   # In main loop, every 1 second:
   loco.ble.send_telemetry(velocity_cms, pressure, temps, int(loco.mech.current))
   loco.ble.process_telemetry()  # Must call to actually send queued data
   ```

4. Monitor serial console for telemetry output:
   ```
   SPD:12.5 PSI:35.2 T:95/210/45 SRV:102  (243 kPa)
   ```

---

## Performance Issues

### Control Loop Running Slower Than 50Hz

**Symptoms:**
- Loop timing > 20ms per iteration
- Servo response sluggish
- BLE telemetry delayed

**Possible Causes:**
1. **Excessive sensor oversampling** - Too many ADC reads
2. **Memory management overhead** - GC running too often
3. **Blocking operations** - Sleep or blocking I/O in loop
4. **CPU frequency too low** - ESP32 not at 240MHz

**Solutions:**
1. Profile loop timing:
   ```python
   # Add to app/main.py run() loop:
   loop_start = time.ticks_ms()
   # ... control loop code ...
   elapsed = time.ticks_diff(time.ticks_ms(), loop_start)
   print(f"Loop: {elapsed}ms")  # Should be < 20ms
   ```

2. Reduce ADC oversampling in `app/sensors.py`:
   ```python
   ADC_SAMPLES = 5  # Reduce from default 10
   ```

3. Adjust GC threshold to reduce frequency:
   ```python
   GC_THRESHOLD = 40000  # Reduce from 61440 (more memory, less frequent GC)
   ```

4. Verify CPU frequency:
   ```python
   >>> import machine
   >>> machine.freq()  # Should return 240000000 (240MHz)
   >>> machine.freq(240000000)  # Set to max if lower
   ```

---

### Heap Fragmentation After Extended Operation

**Symptoms:**
- `MemoryError` after running for hours
- `gc.mem_free()` shows available memory but allocations fail
- System becomes unstable over time

**Possible Causes:**
1. **Memory leak** - Objects not being released
2. **Heap fragmentation** - Free memory in small non-contiguous blocks
3. **Event buffer growth** - Circular buffer not wrapping correctly

**Solutions:**
1. Force aggressive garbage collection:
   ```python
   >>> import gc
   >>> gc.collect()
   >>> gc.collect()  # Call twice for thorough cleanup
   >>> print(gc.mem_free())
   ```

2. Monitor memory usage over time:
   ```python
   # Add to main loop:
   if loop_count % 100 == 0:  # Every 100 loops
       print(f"Free: {gc.mem_free()} bytes")
   ```

3. Check event buffer wrapping:
   ```python
   >>> len(loco.event_buffer)  # Should never exceed EVENT_BUFFER_SIZE (20)
   ```

4. Reboot system periodically (e.g., after 8 hours):
   ```python
   # In run() loop:
   if time.ticks_ms() > 28800000:  # 8 hours
       machine.reset()
   ```

---

## Safety & Watchdog Issues

### Watchdog Triggers on Power Loss

**Symptoms:**
- System shuts down with "PWR_LOSS" error
- Track voltage drops below 1.5V
- Locomotive stops on dirty track

**Possible Causes:**
1. **Dirty track** - Poor electrical contact
2. **Insufficient power** - Command station not providing enough current
3. **Power timeout too short** - CV45 too aggressive
4. **No stay-alive capacitor** - No power reserve during contact loss

**Solutions:**
1. Clean track thoroughly

2. Increase power timeout (CV45):
   ```python
   >>> cv[45] = 20  # 2000ms (default: 8 = 800ms)
   >>> save_cvs(cv)
   ```

3. Install stay-alive capacitor (1F @ 5.5V) for power buffer

4. Check track voltage at locomotive:
   ```python
   >>> from app.sensors import SensorSuite
   >>> sensors = SensorSuite()
   >>> sensors.read_track_voltage()  # Should be 12000-18000 mV
   ```

5. Verify DCC booster can provide sufficient current (2-5A typical)

---

### Cannot Recover from Emergency Shutdown

**Symptoms:**
- System won't restart after emergency shutdown
- Stuck in deep sleep
- REPL not responding

**Possible Causes:**
1. **Deep sleep requires power cycle** - By design, not a fault
2. **Watchdog still detecting fault** - Thermal condition not resolved
3. **Corrupted flash** - Config or log file damaged

**Solutions:**
1. **Power cycle locomotive** - Remove from track for 10 seconds, replace

2. Check black box logs to identify cause:
   ```python
   >>> import json
   >>> with open('error_log.json', 'r') as f:
   ...     logs = json.load(f)
   >>> print(logs[-1])  # Most recent shutdown
   ```

3. If thermal fault, verify temperature has dropped:
   - Wait for boiler/superheater to cool
   - Check logic bay temperature with hand (should be warm, not hot)

4. If system won't boot after power cycle, perform factory reset:
   ```python
   >>> import os
   >>> os.remove('config.json')
   >>> os.remove('error_log.json')
   >>> import machine
   >>> machine.reset()
   ```

---

## Debug Techniques

### Enable Verbose Logging

Add debug prints to main loop:
```python
# In app/main.py run() loop:
if loop_count % 10 == 0:  # Every 10 loops (0.2s)
    print(f"DEBUG: Speed={dcc_speed} Reg={regulator_percent:.1f}% "
          f"Servo={int(loco.mech.current)} Temp={temps[0]:.1f}°C")
```

### Monitor Watchdog State

```python
# In app/safety.py Watchdog.check():
print(f"WDT: Logic={t_logic:.1f} Boiler={t_boiler:.1f} Super={t_super:.1f} "
      f"TrackV={track_v} DCC={dcc_active}")
```

### Capture Telemetry to File

```python
# In main loop:
with open('telemetry.log', 'a') as f:
    f.write(f"{time.ticks_ms()},{velocity_cms},{pressure},{temps[0]},{temps[1]},{temps[2]}\n")
```

### Test Individual Subsystems

```python
# Test sensors:
>>> from app.sensors import SensorSuite
>>> sensors = SensorSuite()
>>> sensors.read_temps()
>>> sensors.read_pressure()
>>> sensors.read_track_voltage()

# Test servo:
>>> from app.actuators import MechanicalMapper
>>> from app.config import load_cvs
>>> cv = load_cvs()
>>> mapper = MechanicalMapper(cv)
>>> mapper.set_goal(50.0, False, cv)
>>> mapper.update(cv)

# Test DCC decoder:
>>> from app.dcc_decoder import DCCDecoder
>>> decoder = DCCDecoder(cv)
>>> decoder.is_active()
>>> print(decoder.current_speed, decoder.direction)
```

---

## Getting Help

If issues persist after trying these solutions:

1. **Check Serial Console Output** - Most errors print to serial console
2. **Review Black Box Logs** - `error_log.json` contains shutdown history
3. **Verify Hardware** - Test sensors, servo, power supplies with multimeter
4. **Check CV Configuration** - Ensure CVs are appropriate for your locomotive
5. **Test with Minimal Configuration** - Disable BLE, reduce features to isolate issue

**Common Root Causes:**
- 80% of issues are wiring/connection problems
- 15% are calibration or CV configuration issues
- 5% are code/firmware bugs

---

## See Also

- [DEPLOYMENT.md](DEPLOYMENT.md) - Installation and setup guide
- [CV.md](CV.md) - Complete CV reference
- [FUNCTIONS.md](FUNCTIONS.md) - API reference and function descriptions
- [capabilities.md](capabilities.md) - System features and limitations

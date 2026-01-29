# BLE Telemetry System

## What It Is

The BLE (Bluetooth Low Energy) telemetry system is your **wireless window** into the locomotive's vital signs. It broadcasts real-time data about temperature, pressure, speed, and system status to your phone or computer without wires.

---

## What It Does

Every second, the system sends a status update containing:
- **Velocity** - How fast the locomotive is moving (cm/s)
- **Pressure** - Current boiler pressure (kPa; PSI in brackets)
- **Temperatures** - Three readings: logic board, boiler, superheater (°C)
- **Servo position** - Regulator valve position (PWM microseconds)
- **DCC speed** - What speed command the decoder received (0-127)
- **Loop counter** - System uptime indicator

All this happens **invisibly in the background** while the locomotive runs normally.

---

## Why It Matters

### Real-Time Monitoring
Watch your locomotive's performance without stopping it or reading gauges. See temperature trends before they become problems.

### Troubleshooting
When something goes wrong, telemetry data shows you exactly what was happening:
- Was the boiler overheating?
- Did pressure get too high?
- Was the servo responding correctly?

### Performance Tuning
Optimize your running by seeing how changes affect behavior:
- Does increasing fire improve response?
- Is pressure stable under load?
- Are temperatures within safe limits?

---

## How to Use It

### 1. Connect via BLE
**On iOS/iPadOS:**
1. Open the **LightBlue** app (free from App Store)
2. Look for device named "TinyPICO" in nearby devices
3. Tap to connect
4. Select "Nordic UART Service"
5. Enable notifications on RX characteristic

**On Android:**
1. Open **nRF Connect** app (free from Play Store)
2. Scan for devices
3. Connect to "TinyPICO"
4. Expand "Nordic UART Service"
5. Enable notifications (down arrow icon)

**On Computer:**
- Use **Adafruit Bluefruit LE Connect** (Windows/Mac/Linux)
- Connect to "TinyPICO"
- Open UART terminal

### 2. Read the Data

You'll see messages like this every second:
```
V:25.3 P:35.2 T:68.1,95.3,215.7 S:1600 D:64 L:15023
```

**What each field means:**
- `V:25.3` - Velocity: 25.3 cm/s (0.253 m/s, about 0.9 km/h, 3.6 scale MPH)
- `P:35.2` - Pressure: 243 kPa (35.2 PSI)
- `T:68.1,95.3,215.7` - Temps: Logic 68.1°C, Boiler 95.3°C, Superheater 215.7°C
- `S:1600` - Servo: 1600µs PWM (slightly open)
- `D:64` - DCC speed command: 64 (50% throttle)
- `L:15023` - Loop counter: 15,023 iterations (about 5 minutes uptime)

### 3. Watch for Problems

**Normal Operation:**
```
V:25.3 P:35.2 T:68.1,95.3,215.7 S:1600 D:64 L:15023
V:26.1 P:35.5 T:68.3,95.8,216.2 S:1620 D:66 L:15073
V:27.0 P:35.3 T:68.5,96.2,217.1 S:1640 D:68 L:15123
```
- Smooth changes in velocity
- Pressure stable around target (241 kPa [35 PSI])
- Temperatures rising slowly

**Warning Signs:**
```
V:15.2 P:42.8 T:73.5,108.3,245.6 S:1800 D:64 L:23400
```
- Pressure high (295 kPa [42.8 PSI], target 241 kPa [35 PSI])
- Boiler temp approaching limit (108°C, limit is 110°C)
- Superheater very hot (245°C, limit is 250°C)
- **Action:** Reduce fire, check water level

---

## What Makes It Special

### Non-Blocking Design
The telemetry system is designed to **never interfere** with locomotive control. Even if Bluetooth is slow or disconnected, the locomotive keeps running perfectly.

**How it works:**
1. System quickly formats data (~0.5ms)
2. Data goes into a queue (instant)
3. Transmission happens later when time permits
4. Control loop continues without waiting

**Benefit:** You get smooth servo operation and perfect DCC packet reception, even during wireless transmission.

### Automatic Recovery
If BLE connection drops:
- Locomotive keeps running normally
- Data queues up (up to 10 seconds worth)
- When reconnected, queue drains automatically
- No data loss for recent events

---

## Real-World Example

**Scenario:** You're running your locomotive on a club layout. Another member asks about its performance.

**Without telemetry:**
- Stop the locomotive
- Read pressure gauge (if visible)
- Guess at temperatures
- Resume running

**With telemetry:**
- Pull out phone
- Open BLE app
- See real-time data streaming
- Answer questions while locomotive keeps running
- Spot potential issues before they become problems

---

## Range and Limitations

### Bluetooth Range
- **Typical:** 5-10 metres line-of-sight
- **Through obstacles:** 2-5 metres
- **Interference:** Metal structures, other 2.4GHz devices reduce range

**Tips for best range:**
- Stay within 5 metres for reliable connection
- Avoid thick metal barriers
- Minimize Wi-Fi/Bluetooth congestion

### Data Rate
- **Update frequency:** 1 packet per second
- **Latency:** <100ms typically
- **Packet size:** ~60 bytes (minimal bandwidth)

**Why 1 second updates:**
- Steam locomotive dynamics are slow (seconds, not milliseconds)
- Reduces radio congestion
- Conserves battery on receiving device
- Plenty fast enough for monitoring

---

## Battery Impact

### On TinyPICO
- BLE transmitter draws ~15mA additional current
- Negligible compared to servo (200mA) and heaters (100-200mA)
- Can be left on continuously without concern

### On Your Phone/Tablet
- BLE is "Low Energy" - minimal battery drain
- Comparable to leaving screen on
- Hour of monitoring uses <5% battery typically

---

## Privacy and Security

### Device Name
- Broadcasts as "TinyPICO" by default
- Visible to all nearby Bluetooth devices
- **Future enhancement:** Configurable name via CV

### Data Security
- No encryption (data not sensitive)
- No authentication (anyone can connect)
- Read-only (no commands accepted via BLE)

**Why no security:**
- Telemetry is not confidential
- Short range (~10m) provides physical security
- No remote control prevents tampering
- Simpler code = more reliable operation

---

## Monitoring Applications

### Recommended Apps

**iOS/iPadOS:**
- **LightBlue** (free, easiest for beginners)
- **nRF Connect** (free, more features)
- **Bluefruit Connect** (free, graphing capability)

**Android:**
- **nRF Connect** (free, industry standard)
- **Serial Bluetooth Terminal** (free, logging)
- **Bluefruit Connect** (free, cross-platform)

**Computer:**
- **Adafruit Bluefruit LE Connect** (all platforms)
- **nRF Connect for Desktop** (advanced features)

### Custom Applications
The Nordic UART Service is an industry standard. You can write your own monitoring app using:
- **iOS:** CoreBluetooth framework
- **Android:** Bluetooth LE APIs
- **Python:** bleak library
- **JavaScript:** Web Bluetooth API

Example Python script:
```python
import asyncio
from bleak import BleakClient

async def monitor():
    async with BleakClient("TinyPICO") as client:
        def callback(sender, data):
            print(data.decode('utf-8'))
        
        await client.start_notify(rx_uuid, callback)
        await asyncio.sleep(3600)  # Monitor for 1 hour

asyncio.run(monitor())
```

---

## Troubleshooting

**Q: Can't find "TinyPICO" device**
- Check TinyPICO is powered on
- Verify BLE is enabled on your device
- Try moving closer (within 3 metres)
- Restart BLE on your device

**Q: Connection keeps dropping**
- Reduce distance to locomotive
- Remove metal obstacles between devices
- Check for 2.4GHz interference (Wi-Fi routers)
- Other BLE devices may be congesting radio

**Q: Data seems delayed**
- Normal - up to 1 second latency is expected
- Check signal strength (RSSI) in BLE app
- Move closer if RSSI below -80 dBm

**Q: Some packets missing**
- Normal during RF congestion
- System prioritizes control over telemetry
- Missing telemetry doesn't affect locomotive operation

---

## Safety Notes

✅ **Telemetry is informational only:**
- Cannot control locomotive via BLE
- Cannot change configuration remotely
- Cannot trigger emergency shutdown

⚠️ **Don't rely solely on telemetry:**
- Always monitor locomotive visually
- Have fire extinguisher nearby
- Know manual shutdown procedure
- Telemetry supplements, doesn't replace, observation

---

**For technical implementation details, see:** [nonblocking-telemetry-technical.md](nonblocking-telemetry-technical.md)

**Version:** 1.0  
**Last Updated:** 28 January 2026

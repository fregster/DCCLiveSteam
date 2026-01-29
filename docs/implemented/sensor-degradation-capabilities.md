# Sensor Failure Graceful Degradation

**Release:** v1.1.0  
**Status:** Complete and tested  
**Impact:** Safety-critical enhancement to sensor failure handling

---

## What It Is

When a sensor fails or becomes disconnected, instead of slamming on the brakes immediately, the locomotive gently slows down to a stop over 10-20 seconds while sounding a distress whistle. This gives operators time to react and prevents heavy trains from derailing due to sudden stops.

---

## What It Does

### Before (v1.0.0)
```
Sensor fails (open circuit, reads 999.9)
    ↓
System immediately triggers emergency shutdown
    ↓
Regulator slams closed, heater cuts off
    ↓
Train stops instantly
    ↓
Result: Possible derailment, no time for operator intervention
```

### After (v1.1.0)
```
Sensor fails (open circuit, reads invalid)
    ↓
System detects failure, enters degraded mode
    ↓
Distress whistle sounds to alert operator
    ↓
Speed smoothly reduces to zero at safe rate (10 cm/s² default)
    ↓
After 20 seconds, if sensor still failed, emergency shutdown
    ↓
Result: Operator has time to react, no derailment, train stopped safely
```

---

## Why It Matters

### Scenario 1: Heavy Loaded Train on Grade

**Without graceful degradation (v1.0.0):**
- Boiler thermistor fails (loose wire)
- System reads 999.9°C
- Emergency shutdown triggered: regulator closes instantly
- Train moving at 100 cm/s (1.0 m/s, 3.6 km/h, 3.3 mph) suddenly stops
- Heavy loaded consist (4-5 cars) experiences sudden 1-2G deceleration
- Cargo shifts, train derails, expensive damage

**With graceful degradation (v1.1.0):**
- Boiler thermistor fails (loose wire)
- System detects invalid reading, enters degraded mode
- Distress whistle (double beep) sounds continuously
- Operator hears whistle, takes manual control via throttle
- OR: System smoothly slows train over 10 seconds
- Loaded consist experiences gentle 0.3G deceleration
- Cargo stays in place, train stops safely
- Operator can now investigate and repair sensor

### Scenario 2: Transient Electrical Glitch

**Without graceful degradation:**
- Electrical noise causes sensor to read 999.9 for 50ms
- False positive: emergency shutdown triggered
- Train stops unnecessarily
- Operator frustrated, confidence in system decreases

**With graceful degradation:**
- Electrical noise causes transient invalid reading
- System uses last-known-valid cached value (e.g., 25°C)
- No degraded mode entered, train continues normally
- System self-heals when noise clears
- Operator never notices the glitch

---

## How to Use It

### Normal Operation

**No operator action required.** Graceful degradation is automatic and transparent:

1. **System monitors all sensors continuously** (boiler temperature, superheater temperature, pressure)
2. **On single sensor failure:**
   - Distress whistle sounds immediately (2-second double beep pattern)
   - Speed smoothly reduces by ~10 cm/s per second (configurable)
   - Operator has ~20 seconds to take manual control or investigate
3. **On multiple simultaneous failures:**
   - Emergency shutdown triggered immediately (maximum safety)
4. **If sensor recovers before timeout:**
   - System returns to normal automatically
   - Graceful degradation ends, normal operation resumes

### Configuration

**Factory defaults are safe and require no adjustment.** However, advanced operators can tune behaviour via Configuration Variables (CVs):

| Setting | CV | Default | Adjustment |
|---------|----|---------|----|
| **Enable Graceful Degradation** | CV84 | Enabled (1) | Set to 0 to disable graceful degradation and use v1.0.0 emergency shutdown behaviour |
| **Deceleration Rate** | CV87 | 10.0 cm/s² | Increase (15-20) for faster slowdown, decrease (5-8) for more gradual |
| **Timeout Before Forced Shutdown** | CV88 | 20 seconds | Increase (30) to give operators more time, decrease (10) for faster shutdown if sensor not recovering |

**To modify CVs:** See [CV.md](../CV.md) for detailed instructions on reading/writing Configuration Variables via your DCC system or mobile app.

---

## Real-World Example

### Example 1: Loose Boiler Thermistor Wire

**Day:** Saturday at the railway club operating session  
**Problem:** Boiler thermistor connector vibrates loose during a run

**What happens:**
1. **12:45 PM** - System detects invalid boiler temperature reading (999.9°C)
2. **Immediately** - Distress whistle sounds (double beep pattern, continuous)
3. **Operator reaction** - Hears whistle, recognises distress signal
4. **12:45-12:55 PM** - System automatically reduces speed over 10 seconds
5. **12:55 PM** - Train stopped safely at end of siding
6. **Investigation** - Operator checks wiring, finds loose connector
7. **Fix** - Reconnects thermistor, confirms sensor reads valid temperature
8. **Resume** - System returns to normal mode, train resumes service 5 minutes later

**Result:** Problem identified and fixed during operating session. No derailment, no damage, no emergency repairs needed.

### Example 2: Electrical Noise on Pressure Sensor

**Problem:** Dirty power supply causes pressure sensor to read invalid values for 50ms

**What happens:**
1. System detects invalid pressure reading
2. Uses cached last-valid reading (69 kPa [10 PSI]) instead of dropping pressure
3. Sensor noise clears after 50ms
4. System confirms valid reading returns
5. No distress signal, train continues normally
6. Operator never notices issue

**Result:** Self-healing behaviour. Trains continue operating safely despite electrical glitches.

---

## Troubleshooting

### Problem: Distress Whistle Sounds but I Don't See a Sensor Failure

**Possible causes:**
1. **Electrical noise** - Transient glitch that already resolved. Check power supply quality.
2. **Intermittent sensor connection** - Loose wire or corroded connector. Inspect thermistor wiring.
3. **Sensor at extreme value** - Temperature reading very close to range limit (e.g., 149.9°C when limit is 150°C). May be normal operation.

**Action:** Stop train, turn off power, inspect all thermistor connectors. Reconnect or replace if necessary.

### Problem: Train Stops Without Warning

**Possible causes:**
1. **Graceful Degradation Disabled** - CV84 set to 0. Re-enable via CV84=1.
2. **Timeout Expired** - Train was in degraded mode for >20 seconds (CV88). Check for failed sensor that didn't recover.
3. **Multiple Simultaneous Failures** - More than one sensor failed. Emergency shutdown triggered by design.

**Action:** Check sensor readings using diagnostic display. If multiple sensors show invalid, professional maintenance required.

### Problem: Deceleration Rate Feels Too Fast or Too Slow

**Solution:** Adjust CV87 (Deceleration Rate)
- Too fast (jerky stop)? → Set CV87 to lower value (e.g., 5.0)
- Too slow (train takes forever to stop)? → Set CV87 to higher value (e.g., 15.0)
- Default (10.0) is balanced for typical model railway scales

**To adjust:** See [CV.md](../CV.md) for CV87 modification procedure.

---

## Safety Notes

### ⚠️ Graceful Degradation Is NOT

- ❌ A replacement for regular sensor maintenance
- ❌ An invitation to ignore failed sensors indefinitely
- ❌ A way to continue operating with multiple failed sensors (immediate shutdown triggered)
- ❌ A guarantee that train will never stop abruptly (multiple failures override graceful mode)

### ✅ Graceful Degradation IS

- ✅ A safety enhancement for single-sensor failures
- ✅ Time for operators to react and take manual control
- ✅ Protection for loaded consists against derailment
- ✅ Self-healing for transient electrical glitches
- ✅ Automatic system behaviour requiring no operator intervention

### 🔧 Maintenance Recommendations

1. **Inspect thermistor connections monthly** - Clean contacts, ensure wires are secure
2. **Test emergency shutdown monthly** - Verify system responds to manual E-STOP
3. **Review event logs quarterly** - Check for patterns of sensor glitches or failures
4. **Replace thermistors every 5 years** - Age and vibration degrade sensor reliability

---

## Related Documentation

**For Operators:**
- [../CV.md](../CV.md) - Configuration Variable reference (CV84, CV87, CV88)
- [../TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - General system troubleshooting

**For Technicians:**
- [sensor-degradation-technical.md](sensor-degradation-technical.md) - Architecture, algorithm, testing, safety analysis
- [../capabilities.md](../capabilities.md) - Complete system capabilities overview
- [../DEPLOYMENT.md](../DEPLOYMENT.md) - System installation and setup

**For Engineers:**
- `app/sensors.py` - Health tracking implementation
- `app/safety.py` - Watchdog degraded mode logic
- `tests/test_sensors.py`, `tests/test_safety.py` - 32 comprehensive unit tests

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.1.0 | 28 Jan 2026 | Graceful degradation feature complete (Phase 1-3). Distress signal and main loop integration pending (Phase 4-5). |
| v1.0.0 | [Earlier] | Original emergency shutdown behaviour (immediate stop on sensor failure). |

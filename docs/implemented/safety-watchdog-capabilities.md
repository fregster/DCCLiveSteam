# Safety Watchdog System

## What It Is

The **Safety Watchdog** is an automatic safety monitor that runs constantly while your locomotive is operating. It watches for dangerous conditions and automatically shuts down the locomotive if something goes wrong.

Think of it as a guardian that asks three questions every 50 times per second:
1. **Is the locomotive too hot?** (boiler, superheater, or controller)
2. **Can we still hear from the command station?** (DCC signal and track power)
3. **Is the system running smoothly?** (memory and timing)

If ANY of these questions get an unsafe answer, the watchdog immediately triggers the emergency shutdown sequence to keep your locomotive safe.

---

## What It Does

### Three Safety Vectors

**Vector 1: Temperature Monitoring**
The watchdog watches three temperature sensors:
- **Logic Temperature (CV41, default 75°C):** Temperature inside the TinyPICO microcontroller
- **Boiler Temperature (CV42, default 110°C):** Steam boiler pressure vessel
- **Superheater Temperature (CV43, default 250°C):** Superheating tubes for dry steam

If ANY temperature exceeds its limit, the system immediately:
1. Shuts down heaters
2. Vents pressure safely (whistle position for 5 seconds)
3. Saves event log to flash memory
4. Closes regulator
5. Enters deep sleep (requires manual power cycle to recover)

**Vector 2: Signal Integrity**
The watchdog listens for two signals:
- **DCC Command Signal (CV44, default 2 seconds):** Commands from your command station controller
- **Track Power (CV45, default 3 seconds):** 12V power on the rails

If signal is lost for longer than the timeout:
1. Watchdog assumes you cannot control the locomotive
2. Triggers emergency shutdown (same 6-second sequence as temperature fault)
3. Protects locomotive from uncontrolled runaway

**Vector 3: System Health**
The watchdog monitors:
- **Free Memory:** Less than 5KB available RAM triggers shutdown (prevents memory crash)
- **Loop Timing:** If control loop takes longer than 20ms, shutdown triggered (ensures 50Hz responsiveness maintained)

### Automatic Response

When the watchdog detects an unsafe condition:

```
Fault Detected (e.g., boiler reaches 110°C)
    ↓
Watchdog.check() returns reason (e.g., "THERMAL_BOILER_LIMIT")
    ↓
Main loop immediately calls die(reason)
    ↓
Emergency shutdown sequence starts:
  1. Heaters OFF (instantly)
  2. Whistle ON for 5 seconds (pressure relief + audible alert)
  3. Event log saved to flash
  4. Regulator closed (before power drains)
  5. System enters deep sleep
    ↓
Locomotive is now safe
```

**Total response time:** 0-20ms to detect + start shutdown sequence

---

## Why It Matters

### Safety Guarantee #1: Thermal Protection
Without the watchdog, boiler could continue heating beyond safe limits:
- **Boiler overheats:** Water boils away, superheater exposed to direct flame → catastrophic failure
- **Superheater overheats:** Steam pipes corrode and fail → hot steam everywhere
- **Controller overheats:** Electronics fail, potentially losing all control

**The watchdog prevents this** by automatically shutting down when temperatures get too high.

### Safety Guarantee #2: Runaway Prevention
Without the watchdog, loss of command signal could cause runaway:
- **DCC signal lost:** Command station disconnected, no speed commands sent
- **Track power lost:** Locomotive could coast downhill with no brakes
- **Operator distracted:** Controller dropped or out of range

**The watchdog prevents this** by stopping the locomotive if signal is lost.

### Safety Guarantee #3: System Stability
Without the watchdog, a glitch could crash the controller:
- **Memory leak:** Free RAM gradually consumed, system becomes unstable
- **Control loop overrun:** Other tasks taking too long, losing 50Hz synchronisation
- **Sensor failure:** Invalid reading causes calculation errors

**The watchdog prevents this** by shutting down gracefully if system health degrades.

### Configurable Safety Margins

You can adjust the watchdog sensitivity using Configuration Variables (CVs):

| Parameter | CV | Default | You Can Change To |
|-----------|----|---------|--------------------|
| Logic Temperature Limit | 41 | 75°C | 60-90°C |
| Boiler Temperature Limit | 42 | 110°C | 90-130°C |
| Superheater Temperature Limit | 43 | 250°C | 200-280°C |
| DCC Timeout | 44 | 2 seconds | 1-5 seconds |
| Power Loss Timeout | 45 | 3 seconds | 1-5 seconds |

**Conservative defaults** are pre-configured for safety. Only adjust if you understand the implications.

---

## How to Use It

### Normal Operation (Watchdog Invisible)

In normal operation, you won't interact with the watchdog. Just operate your locomotive normally:

1. Power on both command station and locomotive
2. Send speed commands
3. Operate functions (lights, whistle, etc.)
4. Watchdog runs silently in background

The watchdog is working perfectly when you don't notice it.

### If Watchdog Triggers (Emergency Shutdown)

If the watchdog detects a problem:

1. **You'll hear the whistle** - 5 second audible alert that something went wrong
2. **Locomotive stops** - Regulator closes after whistle period
3. **TinyPICO LED blinks** - Indicates deep sleep mode (error log saved to flash)
4. **Manual recovery needed** - Turn off power, investigate cause, power back on

**Don't ignore the whistle!** It means something was wrong.

### Understanding the Event Log

When watchdog triggers emergency shutdown, it saves an event log to flash memory:

The event log includes:
- **Timestamp:** When the shutdown occurred
- **Fault reason:** Why it shut down (e.g., "THERMAL_BOILER_LIMIT(112°C > 110°C)")
- **Event buffer:** What happened before shutdown (speeds, temperatures, pressures)

**How to read the log:** Connect to the locomotive via BLE and monitor the telemetry. The last entries before disconnect show conditions at shutdown.

### Adjusting Watchdog Sensitivity

To change watchdog thresholds using your DCC system:

**Example: Raise boiler temperature limit from 110°C to 120°C**

Using your DCC programming track (if supported):
1. Enter service mode programming
2. Set CV42 = 120
3. Exit programming
4. New threshold now active

**⚠️ WARNING:** Only adjust if you understand thermal limits. Too-high limits can damage the locomotive.

---

## Real-World Example

### Scenario 1: Normal Hot Day Operation
```
Morning: 20°C ambient
Afternoon: Locomotive heating naturally as afternoon warms
  15:30 - Boiler: 85°C (cool, lots of margin)
  15:45 - Boiler: 95°C (warming up, still safe)
  16:00 - Boiler: 105°C (getting warm, approaching limit)
  16:15 - Boiler: 110°C (AT LIMIT)
  
  Watchdog detects thermal_boiler_limit
  Stops firing immediately
  Emits 5-second whistle alert
  Closes regulator
  Enters deep sleep

You: "Locomotive getting hot, need to let it cool"
```

### Scenario 2: Power Loss Incident
```
DCC command station loses power (power strip accidentally unplugged)
  T=0ms   - Last valid DCC command received
  T=1000ms - Locomotive still running (momentum)
  T=2000ms - Watchdog says "No command for 2 seconds, must be signal loss"
  T=2050ms - Emergency shutdown triggered
  
  Heaters off
  Whistle vents for 5 seconds
  Log saved
  Regulator closed
  Deep sleep engaged

Result: Locomotive safe, no runaway
```

### Scenario 3: DCC Timeout Configuration
```
Your command station frequently loses sync (every 1.5 seconds)
This triggers false shutdown - too sensitive

You adjust CV44 from 2000ms to 3000ms (3 seconds)
Now small glitches don't cause emergency shutdown
But true signal loss still detected within 3 seconds

Result: More stable operation, still safe
```

---

## Troubleshooting

### Problem: Locomotive keeps entering emergency shutdown

**Symptom:** Whistle sounds repeatedly, system keeps restarting

**Likely causes:**
1. **Temperature too high** - Check boiler temperature reading via BLE
2. **Loose DCC connection** - Secure wiring to command station
3. **Intermittent track power** - Check rail connections and power supply
4. **Low free memory** - System running out of RAM

**How to diagnose:**
1. Check telemetry via BLE - what's the last temperature reading before shutdown?
2. If thermal: Let locomotive cool down naturally
3. If DCC: Check command station connection
4. If power: Verify track voltage with multimeter
5. If memory: Reduce telemetry frequency or add external storage

### Problem: Watchdog not responding (no emergency shutdown)

**Symptom:** Temperatures keep rising past limit but no shutdown

**Likely causes:**
1. **Temperature sensor not connected** - Safety system failing open
2. **CVs corrupted** - Wrong temperature limits set
3. **Watchdog code disabled** - Development mode left on

**How to diagnose:**
1. Check temperature readings via BLE - are they sensible?
2. If reading 999°C or "---": Sensor disconnected
3. Verify CV41, CV42, CV43 via configuration system
4. Reconnect sensor or replace if failed

### Problem: Watchdog triggers falsely during normal operation

**Symptom:** Emergency shutdown with no obvious cause

**Likely causes:**
1. **Timeout thresholds too tight** - CV44 or CV45 too short
2. **Sensor noise** - Momentary spike in temperature reading
3. **Memory leak** - Free memory gradually depleting
4. **DCC dropouts** - Command station communication unreliable

**How to diagnose:**
1. Check event log for fault reason (thermal vs timeout vs memory)
2. If thermal spikes: May need sensor filtering or shielding
3. If timeout: Check command station reliability, increase CV44/CV45
4. If memory: Contact developer for heap analysis

### Problem: Want to ignore watchdog alerts temporarily

**You can't.** The watchdog cannot be disabled for safety reasons.

**Why:** Disabling safety systems creates dangerous situations. Instead:
- Adjust CV thresholds if limits are wrong
- Fix the underlying problem (leaking water, loose connections, etc.)
- Test in safe environment until confident

---

## Safety Notes

### DO ✅
- Monitor temperature readings regularly during operation
- Let locomotive cool down if boiler gets warm
- Keep DCC signal strong (good antenna placement)
- Ensure track power supply is stable
- Use conservative temperature limits when unsure

### DON'T ❌
- Increase temperature limits beyond your boiler's design specs
- Operate with red (critical) telemetry warnings
- Ignore the emergency shutdown whistle
- Run continuously for hours without cooling breaks
- Modify watchdog code to disable thresholds
- Cover temperature sensors (blocks cooling airflow)

### Emergency Shutdown is Safe
When the watchdog triggers emergency shutdown:
- ✅ Heaters stop (no more heat added)
- ✅ Regulator closes (no more steam released)
- ✅ Log saved (analysis possible)
- ✅ System enters safe state (manual recovery needed)

**This is correct behaviour.** The shutdown happening is proof the watchdog is working.

### Understanding Temperature Margin
Default limits have built-in safety margin:
- **Boiler at 110°C:** Not yet dangerous, but getting warm
- **Superheater at 250°C:** Approaching limits but still protected
- **Logic at 75°C:** Thermal throttling starts here, plenty of margin below 100°C rated max

Margins are intentional - shutdown happens *before* dangerous temperatures.

---

## Related Documentation

**For technical details:** [safety-watchdog-technical.md](safety-watchdog-technical.md)  
**For CV configuration:** [docs/CV.md](../CV.md) - CVs 41-45  
**For emergency shutdown procedure:** [emergency-shutdown-capabilities.md](emergency-shutdown-capabilities.md)  
**For system overview:** [docs/capabilities.md](../capabilities.md)

# Emergency Shutdown System

## What It Is

The emergency shutdown system is the locomotive's **safety net** - an automatic sequence that safely secures your locomotive when something goes wrong. Think of it as the locomotive's ability to "park itself" when it detects danger.

---

## What It Does

When a fault is detected (overheating, signal loss, power failure), the system automatically:

1. **Turns off heaters immediately** - Prevents the boiler from building more pressure
2. **Sounds the whistle for 5 seconds** - Alerts you that something's wrong and releases steam pressure
3. **Saves diagnostic data** - Records what happened so you can fix it later
4. **Closes the throttle** - Brings the locomotive to a safe stop
5. **Goes to sleep** - Enters low-power mode until you manually reset it

The entire sequence takes about 6 seconds and is designed to protect both the locomotive and your track power system.

---

## Why It Matters

Live steam locomotives have real hazards:
- **Boilers can overheat** (dry boil = damaged copper)
- **Superheaters can melt** (250°C+ without steam flow)
- **Electronics can burn** (ESP32 rated to 75°C max)
- **Power loss can strand trains** (capacitor buys time to shut down safely)

The emergency shutdown gives your locomotive the ability to **protect itself** when you're not immediately available or when something unexpected happens.

---

## When It Activates

### Automatic Triggers
- **Overheating** - Any of three temperature sensors exceed their limit
  - Logic board: 75°C
  - Boiler: 110°C
  - Superheater: 250°C
- **Signal loss** - No DCC commands received for 2 seconds
- **Power failure** - Track voltage drops for more than 800ms

### Manual Trigger
- **E-STOP button** - DCC function F12 (emergency stop command)
  - **Different behavior:** Skips whistle and sleep stages
  - **Why:** Lets you recover quickly if it was a false alarm

---

## What You'll See

### Normal Emergency Shutdown
1. Whistle blows continuously for 5 seconds
2. Locomotive slows to a stop
3. Status LED goes dark (deep sleep mode)
4. **Recovery:** Press reset button on TinyPICO board

### E-STOP Shutdown (F12)
1. Locomotive stops immediately (no whistle)
2. Status LED stays on (ready for commands)
3. **Recovery:** Send DCC speed command 0, then throttle up normally

---

## Diagnostic Data Saved

After a shutdown, check `error_log.json` on the TinyPICO's filesystem:

```json
{
  "timestamp": "2026-01-28T14:23:45",
  "reason": "Boiler overheat",
  "temperature_logic": 68.5,
  "temperature_boiler": 112.3,
  "temperature_superheater": 230.1,
  "pressure_psi": 42.0,
  "servo_position": 1650,
  "dcc_speed": 64,
  "power_ok": true,
  "uptime_seconds": 1847
}
```

This tells you exactly what was happening when the fault occurred.

---

## Configuration Options

You can adjust the shutdown thresholds and behavior:

| Setting | Default | What It Controls |
|---------|---------|------------------|
| **CV41** | 75°C | Logic board temperature limit |
| **CV42** | 110°C | Boiler temperature limit |
| **CV43** | 250°C | Superheater temperature limit |
| **CV44** | 2000ms | How long to wait for DCC signal |
| **CV45** | 800ms | How long to wait for track power |
| **CV48** | 30% | How much to open whistle valve |

**Warning:** Increasing thermal limits beyond defaults may damage your locomotive. Only adjust if you understand the risks.

---

## How It Protects You

### Stay-Alive Capacitor Management
The system includes a 1F capacitor that stores enough energy to complete the shutdown even after track power is lost. By turning off heaters **first**, it ensures the capacitor's charge is used for the servo (closing the regulator) rather than being wasted on heating elements.

### Graduated Pressure Relief
Opening the whistle **before** closing the regulator prevents pressure spikes that could damage fittings or safety valves. The 5-second vent drops pressure by 10-20 PSI, making final closure gentle on your piping.

### Black Box Recording
The diagnostic log helps you understand **why** the shutdown happened:
- Was it really overheating, or a bad sensor?
- Did DCC signal drop, or is the decoder misconfigured?
- Was power stable, or is your layout having issues?

This data is invaluable for troubleshooting intermittent problems.

---

## Real-World Example

**Scenario:** You're running your locomotive at a club meet. Another member accidentally triggers a short circuit on the layout, cutting power to all tracks.

**What Happens:**
1. **T+0ms:** Power loss detected
2. **T+10ms:** Heaters turn off (stay-alive capacitor now powers only servo)
3. **T+5010ms:** Whistle finishes 5-second blast (alerts everyone)
4. **T+5510ms:** Regulator closes (locomotive stopped)
5. **T+5560ms:** System enters deep sleep

**Result:** Your locomotive is safely secured, whistle warned nearby operators, and you have diagnostic data showing it was a power loss (not overheating). When power returns, simply press the reset button and you're ready to run again.

---

## Frequently Asked Questions

**Q: Can I disable the whistle?**  
A: No. The whistle is a mandatory safety feature that alerts operators and relieves pressure. Skipping it could damage your boiler.

**Q: What if I accidentally hit E-STOP?**  
A: E-STOP (F12) is recoverable - just send a speed 0 command, then throttle up normally. The locomotive doesn't enter deep sleep.

**Q: How do I recover from a full shutdown?**  
A: Press the physical reset button on the TinyPICO board. Check the error log to understand why it shutdown before running again.

**Q: Will it protect against a stuck regulator?**  
A: No. The shutdown assumes the servo is working. If the servo fails, pressure will be vented by the whistle but you'll need to manually close the regulator.

**Q: Can I test the shutdown without a fault?**  
A: Yes - send the E-STOP command (F12). This triggers the shutdown sequence in a recoverable way.

---

## Safety Notes

⚠️ **The emergency shutdown is not a substitute for proper operation:**
- Always monitor your locomotive when running
- Never exceed safe boiler pressure (35 PSI default)
- Check temperature sensors before each session
- Maintain proper water level in boiler

✅ **The shutdown system provides:**
- Automatic protection when you can't react fast enough
- Graceful degradation during power/signal failures
- Diagnostic data for troubleshooting
- Reduced risk of thermal damage

---

**For technical implementation details, see:** [emergency-shutdown-technical.md](emergency-shutdown-technical.md)

**Version:** 1.0  
**Last Updated:** 28 January 2026

# Slew-Rate Limited Motion Control

## What It Is

**Slew-rate limited motion** means your locomotive's throttle (regulator) moves smoothly from one position to another instead of snapping instantly. It's like a real steam locomotive where the engineer gradually opens the throttle rather than slamming it open all at once.

The system controls how fast the throttle can move using a single setting: **CV49 (Travel Time in milliseconds)**, which specifies how long it takes to move from fully closed to fully open.

---

## What It Does

### Smooth Throttle Motion

When you command a speed change:
```
Without slew-rate (INSTANT):
Command: Go from 0% to 50% open
Result:  Throttle SNAPS to 50% in one control cycle (20ms)
Effect:  Servo screams, gearbox shocked, unrealistic

With slew-rate (SMOOTH):
Command: Go from 0% to 50% open
Result:  Throttle GLIDES to 50% over configured time (e.g., 500ms)
Effect:  Smooth operation, realistic motion, mechanical protection
```

### Real-World Equivalence

Think of it like opening a door:
- **No slew-rate:** Door swings open instantly (jerky, mechanical stress)
- **With slew-rate:** Door smoothly opens (natural, controlled motion)

Steam locomotive throttles work the same way—gradual opening for smooth power application.

### Configuration: CV49 (Travel Time)

CV49 sets the **total time from fully closed to fully open**:

| CV49 Setting | Effect | Characteristics | Best For |
|--------------|--------|-----------------|----------|
| 100ms | Very fast | 1% change per cycle, snappy | Fast/racing runs |
| 200ms | Fast | 2.5% per cycle | Normal operation (fast) |
| **500ms** | **Default** | **2.5% per cycle** | **Most users** |
| 1000ms | Slow | 1.25% per cycle | Shunting/precision |
| 2000ms | Very slow | 0.6% per cycle | Prototype realism |
| 5000ms | Glacial | 0.25% per cycle | Long distance trains |

**How it works:**
```
If CV49 = 500ms (default):
- Every 20ms control cycle, throttle can move max 2.5%
- After 500ms (25 cycles), throttle reaches target
- Smooth linear motion from current position to target

If CV49 = 1000ms (slow):
- Every 20ms, throttle moves max 1.25%
- After 1000ms (50 cycles), throttle reaches target
- Even smoother, more gradual motion
```

### Exception: Emergency E-STOP

When you send an E-STOP command (F12 function):
- ✅ Throttle closes **instantly** (no 500ms delay)
- ✅ Slew-rate is **bypassed** for immediate shutdown
- ✅ Emergency response is fast and decisive

This is the ONLY time slew-rate doesn't apply.

---

## Why It Matters

### Reason #1: Mechanical Protection
Smooth throttle motion protects your servo and gearbox:
- **Without slew-rate:** Servo snaps back and forth, gears wear rapidly
- **With slew-rate:** Gradual motion reduces mechanical stress
- **Result:** Servo lasts 5-10x longer (hundreds of thousands of cycles vs tens of thousands)

### Reason #2: Realistic Operation
Real steam locomotives don't have instant throttles:
- **Prototype behaviour:** Engineer gradually opens regulator for smooth power rise
- **Your model:** Smooth motion looks and feels realistic
- **Result:** More satisfying to operate, better viewer experience

### Reason #3: Pressure Stability
Smooth throttle prevents pressure spikes:
- **Without slew-rate:** Sudden steam admission → pressure spike → boiler stress
- **With slew-rate:** Gradual admission → smooth pressure rise → stable operation
- **Result:** Better boiler stability, less stress on safety system

### Reason #4: Operator Control
Predictable motion makes locomotive easier to control:
- **Without slew-rate:** Hard to make precise speed adjustments (too responsive)
- **With slew-rate:** Throttle moves predictably, easier to hit target speeds
- **Result:** Better shunting precision, smoother operation

### Reason #5: Current Draw Smoothing
Smooth throttle reduces electrical stress:
- **Without slew-rate:** Instant full throttle → large current spike
- **With slew-rate:** Gradual throttle → gradual current rise
- **Result:** Power supply happier, fewer voltage dips

---

## How to Use It

### Operating With Slew-Rate (Automatic)

In normal operation, slew-rate works automatically:

1. Send speed command (via DCC)
2. Locomotive starts accelerating smoothly
3. Reaches commanded speed after CV49ms
4. Continue operating normally

**You don't need to do anything**—slew-rate is built-in.

### Adjusting CV49 for Your Preference

**Using DCC Programming (if your system supports it):**

1. Enter service mode programming
2. Write CV49 with desired time in milliseconds
3. Exit programming
4. New slew-rate is active immediately

**Common settings:**

**Fast (racing):** CV49 = 200ms
- Rapid acceleration for fast trains
- More responsive to throttle commands
- Servo runs harder (wears faster)

**Default (normal):** CV49 = 500ms ← Start here
- Good balance of smooth and responsive
- Realistic steam locomotive feel
- Recommended for most operations

**Smooth (shunting):** CV49 = 1000ms
- Very gradual acceleration
- Perfect for tight shunting moves
- Easier to make precise speed adjustments

**Prototype (realistic):** CV49 = 2000ms
- Mimics real steam locomotive throttle feel
- Very gradual power application
- Impressive to watch

### Understanding Throttle Response

**With CV49 = 500ms (default):**
```
Time:    0ms    You command 50% throttle
         100ms  Throttle at 10% (accelerating)
         200ms  Throttle at 20%
         300ms  Throttle at 30%
         400ms  Throttle at 40%
         500ms  Throttle at 50% (reached target!)

Observation: Smooth acceleration over half second
```

**With CV49 = 1000ms (slow):**
```
Time:    0ms    You command 50% throttle
         200ms  Throttle at 10%
         400ms  Throttle at 20%
         600ms  Throttle at 30%
         800ms  Throttle at 40%
         1000ms Throttle at 50% (reached target)

Observation: Even smoother, takes full second
```

### Emergency E-STOP Response

When you press E-STOP on your command station:
```
Time:    0ms    E-STOP command sent (F12)
         0ms    Throttle INSTANTLY closes to 0%
         (no 500ms delay!)

Result: Immediate locomotive stop
Why: Safety—no delay on emergency
```

---

## Real-World Examples

### Example 1: Smooth Acceleration on the Main Line
```
Scenario: Operating a fast passenger train, CV49 = 500ms

Initial: Locomotive at rest (0% throttle)

You: "Accelerate to line speed"
DCC: Sends speed command 100%

Locomotive: Accelerates smoothly
- 100ms: Throttle at 20%, train starting to move
- 200ms: Throttle at 40%, speed building
- 300ms: Throttle at 60%, getting fast
- 400ms: Throttle at 80%, approaching line speed
- 500ms: Throttle at 100%, smooth acceleration complete

Appearance: Beautiful smooth acceleration, looks realistic
Result: Train reaches line speed with gradual power application
```

### Example 2: Precision Shunting Move
```
Scenario: Coupling freight cars, CV49 = 1000ms (slow)

Initial: Shunting engine at rest

You: "Gentle movement for coupling"
DCC: Sends speed command 20%

Engine: Very gradual acceleration
- 250ms: Throttle at 5%, barely moving
- 500ms: Throttle at 10%, creeping slowly
- 750ms: Throttle at 15%, very deliberate
- 1000ms: Throttle at 20%, reached target

Appearance: Extremely gradual, perfect for precise positioning
Result: Smooth coupling without shock or jerking
```

### Example 3: Emergency Stop Drill
```
Scenario: Normal operation, then emergency

Initial: Locomotive at full throttle (100%)

Hazard: Child runs onto track!
Command: E-STOP sent (F12 button)

Result:
- Throttle INSTANTLY closes to 0%
- No waiting for slew-rate
- Locomotive stops as fast as possible
- Safety system engaged immediately

Appearance: Sudden stop (appropriate for emergency)
Result: Immediate halt, no delay
```

### Example 4: Rapid Direction Reversal
```
Scenario: Shunting, need to reverse direction, CV49 = 500ms

Initial: Running forward at 50% throttle
Target: Reverse at 50% throttle

DCC: Sends reverse command at 50%

Locomotive: First closes forward throttle, then opens reverse
- 0ms:    Forward 50%, Target reverse 50%
- 125ms:  Forward throttle closes (0%)
- 250ms:  Reverse throttle opening
- 375ms:  Reverse 50% reached

Appearance: Gradual deceleration, direction reversal, smooth acceleration backward
Result: Clean reversal without mechanical shock
```

---

## Troubleshooting

### Problem: Locomotive responds too slowly to throttle commands

**Symptom:** Big delay between command and response

**Likely causes:**
1. CV49 set too high (>1000ms)
2. Servo mechanical issue

**Solution:**
1. Check CV49 setting—is it appropriate? (default 500ms)
2. Try reducing CV49 to 300-400ms for faster response
3. Test if servo moves smoothly or is stuck

### Problem: Locomotive responds too quickly/snappy

**Symptom:** Throttle moves instantly, servo sounds stressed

**Likely causes:**
1. CV49 set too low (<200ms)
2. Servo at mechanical limits

**Solution:**
1. Increase CV49 to 500ms (default)
2. Listen for servo whining—if present, increase CV49 to 700ms
3. Test different values until smooth and responsive

### Problem: Throttle gets stuck partway open

**Symptom:** Locomotive throttle opens, then stops, doesn't reach target

**Likely causes:**
1. Servo mechanical jam (gearbox stuck)
2. Servo control circuit failure

**Solution:**
1. Power off locomotive
2. Manually try to move servo arm—should move freely
3. If stuck: Clean gearbox, check for debris
4. If mechanical OK: Servo electronics may be failing

### Problem: Motion isn't smooth—jerky or hesitant

**Symptom:** Throttle moves in steps rather than smoothly

**Likely causes:**
1. CV49 very high + coarse DCC commands
2. Servo control resolution issue

**Solution:**
1. Reduce CV49 to <1000ms for smoother motion
2. Send more frequent DCC commands (command station feature)
3. Check servo cable connection

### Problem: E-STOP doesn't close throttle instantly

**Symptom:** E-STOP takes 500ms to close (slew-rate still applying)

**Likely causes:**
1. E-STOP not being decoded correctly
2. Emergency mode not triggering
3. F12 function not configured

**Solution:**
1. Verify F12 E-STOP function is enabled in your DCC system
2. Check that command station sends F12 on E-STOP
3. Contact developer if E-STOP still slow

---

## Safety Notes

### DO ✅
- Use CV49 = 500ms (default) for normal operation
- Increase CV49 if servo sounds stressed
- Test different values to find what works best
- Use E-STOP when emergency response needed

### DON'T ❌
- Set CV49 below 100ms (too fast, damages servo)
- Set CV49 above 5000ms (control becomes unresponsive)
- Ignore servo whining (sign of mechanical stress)
- Try to force servo if it's stuck
- Adjust CV49 while locomotive is running

### Understanding E-STOP
- E-STOP **always** closes throttle instantly
- E-STOP **bypasses** slew-rate limiting
- E-STOP is for **genuine emergencies only**
- Accidental E-STOP activation is annoying but safe

### Servo Lifespan
- **Good CV49 setting (500ms):** Servo lasts years
- **Too fast CV49 (<200ms):** Servo burns out in months
- **Too slow CV49 (>2000ms):** Not a problem, just unresponsive
- **Listen to servo:** If whining, increase CV49

---

## Related Documentation

**For technical details:** [motion-control-technical.md](motion-control-technical.md)  
**For CV configuration:** [docs/CV.md](../CV.md) - CV49  
**For E-STOP operation:** [docs/FUNCTIONS.md](../FUNCTIONS.md) - F12  
**For real locomotive physics:** [physics-engine-capabilities.md](physics-engine-capabilities.md) (if available)  
**For system overview:** [docs/capabilities.md](../capabilities.md)

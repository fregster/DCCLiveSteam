# Prototypical Physics Engine

## What It Is

The **Physics Engine** is the brain that converts your DCC speed commands into accurate model locomotive movement. It ensures your model behaves like a real steam locomotive by:

1. **Converting DCC speed (0-127)** to throttle position (0-100%)
2. **Accounting for steam pressure** - low pressure = reduced power
3. **Scaling to your model** - 80 KPH prototype becomes appropriate model cm/s

The result: Your model locomotive speed control feels intuitive and realistic because the speeds actually reflect real physics.

---

## What It Does

### Three-Stage Conversion Process

```
You send DCC speed command 64 (half throttle)
│
├─ Stage 1: Convert to throttle
│  └─ DCC 64 → 50% throttle open
│
├─ Stage 2: Account for steam pressure
│  └─ If boiler at 50 PSI: Reduce to 25% available power
│
├─ Stage 3: Convert to model velocity
│  └─ HO scale model at 50% throttle, 100 PSI → 12.75 cm/s
│
Result: Locomotive accelerates smoothly and realistically
```

### Stage 1: DCC Speed Command

DCC controllers send speed as **0-127** (128 steps for maximum control granularity).

The Physics Engine converts this to throttle position:
- **DCC 0** → 0% throttle (stopped, E-STOP)
- **DCC 32** → 25% throttle
- **DCC 64** → 50% throttle (half speed)
- **DCC 96** → 76% throttle
- **DCC 127** → 100% throttle (full speed)

### Stage 2: Pressure Compensation

**Real physics:** A steam locomotive without pressure can't make power.

The Physics Engine reduces available power proportionally to boiler pressure:

```
At 100 PSI (full pressure):  Can use 100% of available power
At 80 PSI:  Can use 80% of available power
At 50 PSI:  Can use 50% of available power
At 20 PSI:  Can use 20% of available power
Below 5 PSI: Insufficient steam to move (stops)
```

**Result:** If you command 100% throttle but only have 50 PSI, locomotive moves at 50% power—just like real steam.

### Stage 3: Scale Conversion

**Key insight:** Your model doesn't move at the same speed as a real locomotive!

A real locomotive going 80 KPH ≠ your HO scale model going 80 KPH (that would be flying apart).

The Physics Engine uses **CV39 (prototype speed)** and **CV40 (scale ratio)** to calculate correct model velocity:

```
Formula:
Model velocity (cm/s) = (Prototype KPH × 27.778) / Scale ratio × (Throttle / 100)

Example (HO scale, 80 KPH prototype, full throttle, 100 PSI):
= (80 × 27.778) / 87.1 × (100/100)
= 25.51 cm/s
= About 1.5 meters/minute
= Realistic for HO scale model
```

---

## Why It Matters

### Reason #1: Intuitive Speed Control

Without physics engine:
- Half throttle = arbitrary speed, no relationship to real world
- You don't know what speed to expect
- Operate by trial and error

With physics engine:
- Half throttle = proportionally slower
- 100% throttle = maximum speed you configured
- Speed control feels natural and predictable

### Reason #2: Realistic Pressure Effects

Without physics engine:
- Low boiler pressure has no effect on speed
- Locomotive moves fast even with no steam (unphysical)
- Pressure monitoring becomes meaningless

With physics engine:
- Low pressure automatically reduces speed
- Locomotive won't move if pressure too low
- Pressure management becomes realistic and important

### Reason #3: Scale-Accurate Operation

Without physics engine:
- Speeds are arbitrary
- Model zooms around like a toy car
- Looks nothing like prototypical 80 KPH operation
- Small (N scale) and large (O scale) locos move at same speed

With physics engine:
- N scale express moves at ~1 meter/minute
- HO scale mixed freight moves at ~1.5 meters/minute
- O scale heavy loco moves at ~2 meters/minute
- Each scale looks realistically fast or slow for its type

### Reason #4: Variety Between Locomotives

You might have:
- Fast express passenger locomotive (CV39 = 100 KPH)
- Medium mixed-traffic locomotive (CV39 = 80 KPH)
- Slow heavy freight locomotive (CV39 = 60 KPH)

Each has different characteristics without needing different DCC decoders.

### Reason #5: Configuration Flexibility

Need to change scale? Change CV40.  
Operating different scale? Different CV40 for that loco.  
Want faster/slower locomotive? Adjust CV39.

The Physics Engine makes changes simple and intuitive.

---

## How to Use It

### Basic Operation (Automatic)

In normal operation:
1. You send speed command via DCC
2. Physics Engine converts it to locomotive velocity
3. Locomotive moves at appropriate speed
4. **You don't need to do anything**—it's automatic

### Configuring for Your Locomotive

The Physics Engine needs two pieces of information:

**CV39: Prototype Speed (KPH at full throttle)**
- Set this to the speed your prototype locomotive reaches at full throttle
- Default: 80 KPH (typical express steam locomotive)
- Options:
  - 40 KPH: Slow shunting engine
  - 60 KPH: Heavy freight
  - 80 KPH: Express passenger (normal)
  - 100 KPH: High-speed express
  - 120 KPH: Exceptional high-speed loco

**CV40: Scale Ratio (denominator only)**
- Set this to your model's scale
- Default: 87.1 (HO scale, most common)
- Common values:
  - 20 (G scale, garden railway)
  - 48 (O scale, large models)
  - 87.1 (HO scale, standard model railway)
  - 160 (N scale, small models)

### Example Configurations

**HO Scale Express Locomotive:**
```
CV39 = 80 KPH (prototype speed)
CV40 = 87.1 (HO scale)
Result: Full throttle = 25.51 cm/s ≈ 1.5 m/min
```

**N Scale Mixed Freight:**
```
CV39 = 60 KPH (slower freight)
CV40 = 160 (N scale)
Result: Full throttle = 10.42 cm/s ≈ 0.6 m/min
```

**O Scale Heavy Goods:**
```
CV39 = 50 KPH (very slow)
CV40 = 48 (O scale)
Result: Full throttle = 24.27 cm/s ≈ 1.5 m/min
```

### Understanding Telemetry Velocity

When you monitor BLE telemetry, you see "velocity in cm/s":

```
Telemetry reading: 12.75 cm/s
Meaning: Locomotive currently moving at 12.75 centimeters per second

Converting to meters/minute: 12.75 cm/s × 60 sec/min = 765 cm/min ≈ 7.65 m/min

Prototypical equivalent (HO scale, 80 KPH loco):
This is half throttle, so prototype equivalent ≈ 40 KPH
```

---

## Real-World Examples

### Example 1: Setting Up Express Passenger Locomotive (HO Scale)

**Prototype:** LNER A4 streamliner, 160 KPH design speed, typical operating 90 KPH

**Your model:** HO scale model of same locomotive

**Configuration:**
```
CV39 = 90 KPH    (typical operating speed)
CV40 = 87.1      (HO scale)
```

**Result:**
- Full throttle: 25.51 cm/s (≈1.5 m/min) - looks like fast express
- Half throttle: 12.75 cm/s (≈0.75 m/min) - smooth running
- Quarter throttle: 6.38 cm/s (≈0.4 m/min) - gentle shunting

**Operating experience:** Smooth, proportional control that feels realistic.

### Example 2: Heavy Freight Locomotive (Different Scale)

**Prototype:** Big Boy, 80 KPH full throttle, massive consist

**Your model:** O scale (1:48)

**Configuration:**
```
CV39 = 80 KPH
CV40 = 48       (O scale - much larger model)
```

**Result:**
- Full throttle: 34.72 cm/s (≈2 m/min) - looks appropriate for big model
- Half throttle: 17.36 cm/s (≈1 m/min)
- Quarter throttle: 8.68 cm/s (≈0.5 m/min)

**Observation:** Much faster than HO scale model, but O scale models *are* much bigger, so this looks right.

### Example 3: Pressure Effects (Real-Time Adaptation)

**Scenario:** Operating express locomotive, CV39=80 KPH, CV40=87.1

**Situation 1: Full pressure (100 PSI)**
```
DCC command: Half throttle (64)
Result: 12.75 cm/s (full power available)
```

**Situation 2: Low pressure (50 PSI)**
```
DCC command: Half throttle (64) - same DCC command!
Result: 6.38 cm/s (half the speed!)
Physics: Boiler isn't making enough steam
Effect: You naturally operate differently (faster command) to compensate
```

**Situation 3: Critical low pressure (10 PSI)**
```
DCC command: Even full throttle (127)
Result: Barely crawls (insufficient steam)
Physics: Real steam locomotive behavior
Effect: Alert to check pressure, stoke fire
```

### Example 4: Different Scale, Same Configuration

**Your operating day:**
- 10:00 - Operating HO scale mixed freight (CV39=70, CV40=87.1)
- 11:00 - Switch to N scale express (CV39=90, CV40=160)

**HO half throttle:** 12.25 cm/s (≈0.75 m/min)  
**N half throttle:** 7.81 cm/s (≈0.5 m/min)

Both look appropriately fast for their scale, even though you're using the same throttle position.

---

## Troubleshooting

### Problem: Locomotive moves too fast or too slow

**Symptom:** Speed doesn't match your expectations

**Likely causes:**
1. CV39 wrong (not matching your prototype speed)
2. CV40 wrong (wrong scale configured)

**Solution:**
1. Check CV39 - is it the right prototype speed? (Usually 60-100 KPH)
2. Check CV40 - is it your actual scale? (87.1 for HO, 160 for N, 48 for O)
3. Adjust until speed feels right

### Problem: Low pressure doesn't affect speed

**Symptom:** Moving fast even with low boiler pressure

**Likely causes:**
1. Pressure sensor not working
2. Pressure reading not reaching Physics Engine
3. Physics Engine pressure compensation failed

**Solution:**
1. Check BLE telemetry - what pressure is shown?
2. If pressure reading looks wrong: Check pressure sensor
3. If pressure reading correct but speed not affected: Contact developer

### Problem: Pressure at 0 but locomotive still moving

**Symptom:** "Impossible" - moving with no steam

**Likely causes:**
1. Pressure compensation threshold not working
2. Sensor reading error

**Solution:**
1. Check telemetry for actual pressure value (not display label)
2. If truly at 0 PSI and moving: System error, report to developer
3. Normal: At <5 PSI, locomotive shouldn't move

### Problem: Speed jumps around (not smooth)

**Symptom:** Velocity changes abruptly in telemetry

**Likely causes:**
1. Noisy pressure sensor (readings fluctuating)
2. DCC decoder speed step glitch
3. Pressure compensation threshold effects

**Solution:**
1. Check telemetry - is pressure reading stable or flickering?
2. If flickering: Sensor needs better shielding/filtering
3. If stable: Speed variation is normal due to discrete DCC steps

### Problem: Want to change locomotive speed without adjusting CV39

**Can't - CV39 is permanent per locomotive.**

**Options:**
1. Create different locomotive roster entries (if decoder supports)
2. Set CV39 to average speed, accept some variation
3. Use CV49 (Travel Time) - NO, that's servo speed, not locomotive speed

CV39 is locomotive-specific and should stay constant.

---

## Safety Notes

### DO ✅
- Set CV39 to match your prototype locomotive
- Use correct CV40 for your scale
- Monitor pressure in telemetry (should stay above 50 PSI)
- Stoke fire if pressure drops (see pressure warning)
- Operate different scales with different CV40 values

### DON'T ❌
- Set CV39 to unrealistic values (>150 KPH)
- Ignore pressure compensation effects (low pressure means reduced speed)
- Assume speed is independent of pressure (it's not)
- Set CV40 to 0 or negative (causes errors)
- Ignore telemetry velocity readings

### Understanding Pressure Effects

Low pressure is **automatic and correct** behaviour:
- At 50 PSI, locomotive gets 50% power (not a bug)
- At 20 PSI, locomotive gets 20% power (still working correctly)
- At <5 PSI, locomotive can't move (failsafe)

This is **how it should work.** Pressure management becomes real operational consideration.

### Physical Plausibility

If speeds don't look right, check:
- **Too fast?** Increase CV40 (scale ratio) or decrease CV39
- **Too slow?** Decrease CV40 or increase CV39
- **Variable?** Check pressure reading (likely pressure effect, not bug)

---

## Related Documentation

**For technical details:** [physics-engine-technical.md](physics-engine-technical.md)  
**For CV configuration:** [docs/CV.md](../CV.md) - CVs 39, 40  
**For motion control:** [motion-control-capabilities.md](motion-control-capabilities.md) - CV49  
**For safety watchdog:** [safety-watchdog-capabilities.md](safety-watchdog-capabilities.md)  
**For telemetry:** [nonblocking-telemetry-capabilities.md](nonblocking-telemetry-capabilities.md)  
**For system overview:** [docs/capabilities.md](../capabilities.md)

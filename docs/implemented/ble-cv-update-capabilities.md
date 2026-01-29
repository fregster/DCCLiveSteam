# BLE Configuration Variable (CV) Updates

**Release:** v1.2.0  
**Status:** Complete and tested  
**Impact:** Over-the-air configuration without USB connection

---

## What It Is

Change any locomotive Configuration Variable (CV) wirelessly using your phone or tablet via Bluetooth. No USB cable, no bench programming, no powered track required. Send simple text commands like `CV32=20.0` and the locomotive validates, applies, and saves the change instantly.

---

## What It Does

### Before (v1.0.0-v1.1.0)
```
Need to change CV32 (boiler pressure target)?
    ↓
1. Bring locomotive to workshop
2. Connect USB cable to computer
3. Open serial terminal
4. Edit config.json file manually
5. Upload file to locomotive
6. Reboot locomotive
7. Test on track
    ↓
Result: 15-20 minutes to change one CV
```

### After (v1.2.0)
```
Need to change CV32 (boiler pressure target)?
    ↓
1. Open BLE terminal app on phone (e.g., Serial Bluetooth Terminal)
2. Connect to "LiveSteam" device
3. Type: CV32=20.0
4. Press Enter
    ↓
Result: Change applied and saved instantly (< 1 second)
```

---

## Why It Matters

### Scenario 1: Track-Side Tuning During Operating Session

**Problem:** Locomotive runs too fast for new track layout. Need to reduce prototype speed (CV39) from 203 km/h to 160 km/h.

**Old Approach (v1.0.0-v1.1.0):**
- Stop operating session
- Remove locomotive from track
- Take to workshop with laptop
- USB connect, edit config, upload
- Return to track, test
- **Time lost: 20+ minutes**

**New Approach (v1.2.0):**
- Keep locomotive on track
- Pull out phone, open BLE app
- Connect to locomotive BLE
- Send: `CV39=160`
- Immediately see change in telemetry
- **Time lost: < 30 seconds**

### Scenario 2: Fine-Tuning Pressure Control

**Problem:** Boiler pressure oscillates between 16-20 PSI. Want tighter control around 18 PSI.

**Old Approach:**
1. Adjust CV32=18.0 via USB
2. Test run, observe oscillation
3. USB adjust CV32=17.5
4. Test run, observe
5. Repeat 3-4 times
6. **Total tuning time: 1-2 hours**

**New Approach:**
1. Run locomotive, monitor BLE telemetry on phone
2. See oscillation in real-time
3. Send `CV32=18.0` while running
4. Observe immediate effect in telemetry
5. Send `CV32=17.5` if needed
6. **Total tuning time: 5-10 minutes**

### Scenario 3: Multi-Locomotive Fleet Management

**Problem:** Operating 5 locomotives at club meet, each needs DCC address change for new operating plan.

**Old Approach:**
- USB program each locomotive individually
- 5 × 15 minutes = **75 minutes setup time**

**New Approach:**
- BLE connect to each locomotive
- Send `CV1=<new_address>` to each
- 5 × 1 minute = **5 minutes setup time**

---

## How to Use It

### Normal Operation

**1. Connect to Locomotive BLE:**
- Use any BLE terminal app (iOS: "BLE Terminal", Android: "Serial Bluetooth Terminal")
- Scan for devices, look for "LiveSteam"
- Connect (no pairing required)

**2. Send CV Update Command:**
Format: `CV<number>=<value>`

**Examples:**
```
CV32=20.0        Set boiler pressure target to 20.0 PSI
CV49=1200        Set servo travel time to 1200 ms
CV39=180         Set prototype speed to 180 km/h
CV41=70          Set logic bay temp limit to 70°C
CV1=15           Change DCC address to 15
```

**3. Verify Change:**
- Check USB serial output for confirmation message
- Watch telemetry stream for updated behavior
- Changes persist across power cycles (saved to flash)

### Command Format Rules

✅ **Valid Commands:**
- `CV32=20.0` - Float value (pressure, speed, percentages)
- `CV49=1200` - Integer value (time, address, counts)
- `CV1=15` - DCC address
- Spaces are ignored: `CV 32 = 20.0` works

❌ **Invalid Commands:**
- `32=20.0` - Missing "CV" prefix
- `CV32 20.0` - Missing "=" separator
- `CV32=abc` - Non-numeric value
- `CV32=999` - Out of range (max 25.0 for CV32)

### Validation Responses

**Success:**
```
BLE: Updated CV32 (Target pressure) from 18.0 to 20.0 PSI
```

**Rejection:**
```
BLE REJECT: CV32 out of range 15.0-25.0 PSI
BLE REJECT: CV99 unknown (not in validation table)
BLE REJECT: CV32 invalid value 'abc' (not a number)
```

**All responses appear in USB serial output. Future versions will send BLE acknowledgements.**

---

## Real-World Examples

### Example 1: DCC Address Change at Operating Session

**Day:** Saturday club meet, need to reassign locomotive addresses

**Steps:**
1. Open BLE Terminal on phone
2. Connect to first locomotive ("LiveSteam")
3. Type: `CV1=10` (new DCC address)
4. Disconnect, move to next locomotive
5. Repeat for remaining locomotives

**Result:** 5 locomotives addressed in < 5 minutes. No USB cables, no laptop required.

### Example 2: Servo Travel Time Adjustment

**Problem:** Regulator servo moves too slowly (2+ seconds to full open)

**Steps:**
1. BLE connect while locomotive idle on track
2. Current CV49=2000ms (2 seconds)
3. Send: `CV49=1000` (1 second)
4. Test DCC speed command
5. Observe faster servo response
6. If still too slow, send `CV49=800`

**Result:** Optimal servo speed found in 2-3 iterations without removing locomotive from track.

### Example 3: Thermal Limit Tuning for Summer Operation

**Problem:** Hot summer day, logic bay reaches 72°C (close to default 75°C limit)

**Steps:**
1. BLE connect to running locomotive
2. Monitor telemetry for logic temp
3. Send: `CV41=78` (raise limit to 78°C for summer operation)
4. Locomotive continues running safely
5. Before winter, reset: `CV41=75`

**Result:** Seasonal adjustment without workshop visit.

---

## Troubleshooting

### Problem: BLE Connection Fails

**Possible causes:**
1. **Locomotive not powered** - BLE only active when locomotive on
2. **Out of range** - BLE range ~10 meters line-of-sight
3. **Another device connected** - BLE supports 1 client at a time

**Action:** Ensure locomotive powered, move closer, disconnect other devices.

### Problem: Command Sent But No Response

**Possible causes:**
1. **Missing newline** - BLE terminal must send `\n` after command
2. **Command in wrong format** - Must be `CV<num>=<value>`
3. **CV number unknown** - Only CVs in validation table accepted

**Action:** Check command format, verify CV number exists in [CV.md](../CV.md).

### Problem: "Out of Range" Error

**Cause:** Value exceeds safety bounds for that CV.

**Solution:** Check [CV.md](../CV.md) for valid range. Example: CV32 (pressure) must be 15.0-25.0 PSI.

**Example:**
```
CV32=30.0          ❌ Rejected: "CV32 out of range 15.0-25.0 PSI"
CV32=20.0          ✅ Accepted: Within valid range
```

### Problem: CV Change Not Persisting After Reboot

**Possible causes:**
1. **Flash write failed** - Corrupted filesystem, full flash
2. **CV syntax error** - Command appeared to work but didn't save

**Action:**
1. Reboot locomotive, check CV value
2. If not saved, USB connect and check `config.json` file
3. If filesystem corrupted, reflash firmware

---

## Safety Notes

### ⚠️ BLE CV Updates Are NOT

- ❌ A replacement for understanding CV functions (read [CV.md](../CV.md) first)
- ❌ Safe to use while locomotive moving at high speed (stop first)
- ❌ Authenticated (any nearby device can send commands)
- ❌ Reversible with "undo" (change is immediate and persistent)

### ✅ BLE CV Updates ARE

- ✅ Validated against hardcoded safety bounds (cannot bypass)
- ✅ Atomic (failed validation preserves old value)
- ✅ Persistent (saved to flash, survives power cycle)
- ✅ Logged (all attempts recorded in event buffer for audit trail)
- ✅ Non-blocking (doesn't interfere with 50Hz control loop)

### 🔧 Best Practices

1. **Test Before Operating Session:** Try new CV values during test runs, not during public demonstrations
2. **Document Changes:** Keep log of CV changes made via BLE (for future reference)
3. **Conservative Increments:** Change CVs by small amounts (e.g., CV32: 18.0 → 18.5, not 18.0 → 22.0)
4. **Monitor Telemetry:** Watch BLE telemetry stream when adjusting CVs to see immediate effects
5. **Know Valid Ranges:** Familiarize yourself with CV bounds in [CV.md](../CV.md) before adjusting

### 🛡️ Security Considerations

**No Authentication:** BLE commands are not encrypted or authenticated. Any device within range (~10m) can send CV update commands.

**Acceptable Risk:** For model railway environment with trusted operators only. Not suitable for public exhibitions without additional security measures.

**Future Enhancement:** PIN-based BLE pairing may be added in v1.3.0.

---

## Configuration Variables

**All CVs listed in [CV.md](../CV.md) can be updated via BLE.** Most commonly adjusted CVs:

| CV | Parameter | Range | Unit | Typical Use Case |
|----|-----------|-------|------|------------------|
| 1 | DCC Address | 1-127 | address | Operating session address changes |
| 32 | Target Pressure | 15.0-25.0 | PSI | Boiler pressure tuning |
| 39 | Prototype Speed | 100-250 | km/h | Scale speed adjustment |
| 41 | Logic Temp Limit | 60-85 | °C | Seasonal thermal adjustments |
| 42 | Boiler Temp Limit | 100-120 | °C | Dry-boil protection tuning |
| 49 | Servo Travel Time | 500-3000 | ms | Regulator response tuning |
| 84 | Graceful Degradation | 0-1 | bool | Enable/disable sensor degradation mode |

**For complete CV list and descriptions, see [../CV.md](../CV.md).**

---

## Related Documentation

**For Operators:**
- [../CV.md](../CV.md) - Configuration Variable reference (all CVs, valid ranges, descriptions)
- [../capabilities.md](../capabilities.md) - Complete system capabilities overview
- [nonblocking-telemetry-capabilities.md](nonblocking-telemetry-capabilities.md) - BLE telemetry monitoring

**For Technicians:**
- [ble-cv-update-technical.md](ble-cv-update-technical.md) - Architecture, validation logic, testing, timing analysis
- [../DEPLOYMENT.md](../DEPLOYMENT.md) - System installation and BLE setup

**For Engineers:**
- `app/ble_uart.py` - BLE RX infrastructure (_on_rx method, rx_queue)
- `app/config.py` - CV validation (validate_and_update_cv function, CV_BOUNDS dictionary)
- `app/main.py` - Main loop integration (process_ble_commands method)
- `tests/test_ble_uart.py`, `tests/test_config.py` - 22 comprehensive unit tests

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.2.0 | 29 Jan 2026 | BLE CV update feature complete. RX infrastructure, CV validation, main loop integration, 22 unit tests. |
| v1.1.0 | 28 Jan 2026 | Graceful sensor degradation feature. |
| v1.0.0 | [Earlier] | Initial release with BLE telemetry (TX only). |

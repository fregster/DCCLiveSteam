# BLE Configuration Variable (CV) Update - Implementation Plan

**Date Created:** 28 January 2026  
**Status:** Planning  
**Priority:** High  
**Related Feature:** Item 10 - Over-The-Air CV Configuration via BLE

---

## Executive Summary

Allow operators to modify Configuration Variables (CVs) in real-time via Bluetooth LE without requiring USB connection or bench reprogramming. Single CV changes are sent as BLE commands, validated against safe bounds, persisted to flash, and take effect immediately.

**Safety Model:** All CV changes are validated against hardcoded limits before acceptance. Conservative defaults are preserved if any value is out of valid range.

---

## Architecture Overview

### Current BLE System
- **Module:** `app/ble_uart.py`
- **Service:** Nordic UART Service (NUS)
- **Current Usage:** Telemetry TX only (non-blocking queue)
- **Capability:** Full duplex (can receive commands)

### Proposed Additions
```
┌──────────────────────────────┐
│   BLE UART Service (NUS)     │
│  ┌────────────────────────┐  │
│  │  RX Queue (NEW)        │  │
│  │  Command Parser (NEW)  │  │
│  └────────────────────────┘  │
│  ┌────────────────────────┐  │
│  │  Telemetry TX Queue    │  │
│  │  (existing)            │  │
│  └────────────────────────┘  │
└──────────────────────────────┘
         ↓ main.py
    ┌─────────────────┐
    │ CV Validator    │ (NEW)
    │ & Processor     │
    └─────────────────┘
         ↓
    ┌─────────────────┐
    │ config.py       │
    │ save_cvs()      │
    └─────────────────┘
```

---

## Implementation Phases

### Phase 1: BLE Receive Infrastructure (Priority 1)

**Goal:** Enable receiving commands via BLE without interfering with telemetry TX.

**Changes to `app/ble_uart.py`:**

1. **Add RX queue and command buffer:**
```python
class BLE_UART:
    def __init__(self):
        # ... existing telemetry TX queue ...
        self.rx_queue = []          # NEW: Command buffer
        self.rx_buffer = bytearray() # NEW: Accumulation buffer
        self.max_rx_queue = 16       # NEW: Max pending commands
```

2. **Implement RX callback:**
```python
def on_ble_rx(self, data: bytes) -> None:
    """
    Process incoming BLE data. Accumulates until newline.
    
    Why: Commands arrive as ASCII strings with \n terminator.
    Single RX events may contain partial commands.
    
    Args:
        data: Raw bytes from BLE central device
        
    Safety: Max buffer 128 bytes prevents memory exhaustion.
    """
    # Append to buffer, looking for \n
    # On \n, parse command and add to rx_queue
    # If buffer exceeds 128 bytes, discard oldest data
```

3. **Update BLE notify handler:**
- Attach RX callback to BLE UART characteristic
- Process incoming data in non-blocking manner
- Never block 50Hz control loop

**Testing:**
- Unit test: Mock BLE data, verify buffer accumulation
- Unit test: Verify newline-terminated command extraction
- Unit test: Verify buffer overflow protection

---

### Phase 2: CV Update Command Parser (Priority 1)

**Goal:** Parse and validate CV update commands safely.

**Command Format:**
```
CV<number>=<value>\n
```

**Examples:**
```
CV32=20.0\n        # Set boiler pressure setpoint to 20.0 PSI
CV49=1200\n        # Set servo travel time to 1200 ms
CV39=180\n         # Set prototype speed to 180 km/h
```

**New function in `app/config.py`:**

```python
def validate_and_update_cv(cv_num: int, new_value: str) -> Tuple[bool, str]:
    """
    Validates CV number and value against safe bounds.
    Returns (success, message) tuple.
    
    Why: Prevents unsafe CV values (e.g., CV41 > 100°C = thermal runaway).
    Conservative bounds prevent operator errors.
    
    Args:
        cv_num: CV number (integer 1-99)
        new_value: New value as string (may be float or int)
        
    Returns:
        (True, "Updated CV32 to 20.0") on success
        (False, "CV32 out of range 15.0-25.0 PSI") on validation failure
        
    Raises:
        ValueError: If cv_num invalid or value unparseable
        
    Safety: 
        - Rejects CV numbers outside 1-99
        - Rejects values outside hardcoded safe bounds
        - Preserves old value on error (atomic update)
        - Logs update to event buffer for audit trail
    """
```

**CV Bounds Matrix (hardcoded limits):**

| CV | Parameter | Min | Max | Unit | Reason |
|---|---|---|---|---|---|
| 32 | Target Pressure | 15.0 | 25.0 | PSI | Boiler safety envelope |
| 41 | Logic Watchdog | 60 | 85 | °C | TinyPICO thermal range |
| 42 | Boiler Watchdog | 100 | 120 | °C | Dry-boil detection range |
| 43 | Superheater Watchdog | 240 | 270 | °C | Gasket protection range |
| 44 | DCC Timeout | 5 | 100 | 0.1s | 0.5s - 10s reasonable |
| 45 | Power Timeout | 2 | 50 | 0.1s | 0.2s - 5s reasonable |
| 49 | Travel Time | 500 | 3000 | ms | Servo speed envelope |
| 39 | Prototype Speed | 100 | 250 | km/h | Realistic locomotive range |
| 40 | Scale Ratio | 50 | 120 | Ratio | OO/HO/N scale |
| 33 | Stiction Breakout | 10 | 50 | % | Friction range |

**Testing:**
- Unit test: Valid CV updates succeed
- Unit test: Out-of-range values rejected with reason
- Unit test: Invalid CV numbers rejected
- Unit test: Non-numeric values rejected with error message
- Unit test: Event buffer logs all updates (audit trail)

---

### Phase 3: Main Loop Integration (Priority 2)

**Goal:** Process queued CV updates in 50Hz loop without blocking control.

**Changes to `app/main.py` Locomotive class:**

```python
def process_ble_commands(self) -> None:
    """
    Process pending BLE CV update commands.
    
    Why: Non-blocking integration into 50Hz loop.
    Each command fully processed before moving to next.
    
    Safety: 
        - Limits to 1 command per loop iteration
        - Command processing < 5ms (must fit in 20ms budget)
        - Failed commands logged but don't stop loop
    """
    if not self.ble.rx_queue:
        return  # No commands pending
    
    command = self.ble.rx_queue.pop(0)  # FIFO order
    
    try:
        # Parse "CV32=20.0" format
        parts = command.split('=')
        if len(parts) != 2:
            self.log_event("BLE_CMD_ERROR", "Invalid format: " + command)
            return
        
        cv_str = parts[0].strip()
        value_str = parts[1].strip()
        
        if not cv_str.startswith('CV'):
            self.log_event("BLE_CMD_ERROR", "Not a CV command: " + command)
            return
        
        cv_num = int(cv_str[2:])  # Extract number after "CV"
        success, message = validate_and_update_cv(cv_num, value_str)
        
        if success:
            self.cv[cv_num] = float(value_str) if '.' in value_str else int(value_str)
            save_cvs(self.cv)
            self.log_event("BLE_CV_UPDATE", f"CV{cv_num}={value_str}")
            self.ble.queue_telemetry({"ack": f"CV{cv_num} updated"})
        else:
            self.log_event("BLE_CV_REJECTED", message)
            self.ble.queue_telemetry({"error": message})
            
    except (ValueError, IndexError) as e:
        self.log_event("BLE_CMD_PARSE_ERROR", str(e))
        self.ble.queue_telemetry({"error": "Parse error: " + str(e)})
```

**Placement in main loop:**
- After DCC decoder processing
- Before physics/actuator updates
- Non-blocking, single command per cycle

**Testing:**
- Integration test: Valid CV command flows through and updates CV dict
- Integration test: Invalid command logged but loop continues
- Integration test: Multiple commands queued are processed in FIFO order
- Performance test: Command processing < 2ms (well within 20ms budget)

---

### Phase 4: Telemetry Response Messages (Priority 2)

**Goal:** Provide operator feedback on CV update success/failure via BLE.

**New telemetry fields:**
```json
{
  "velocity_cms": 45.3,
  "pressure_psi": 18.5,
  "boiler_temp_c": 105.2,
  "ack": "CV32 updated to 20.0 PSI",
  "error": null
}
```

or on error:
```json
{
  "error": "CV32 out of range 15.0-25.0 PSI",
  "ack": null
}
```

**Implementation:**
- Add optional `"ack"` and `"error"` fields to telemetry JSON
- Field only present if command just processed
- Clears after one telemetry packet
- Operator sees immediate feedback

---

## New Configuration Variables

**No new CVs required.** Existing CVs can be updated via BLE.

However, recommend adding audit trail:
- **CV85:** Enable BLE CV updates (default 1=ON, 0=disabled for security)
- **CV86:** BLE command ACK mode (0=silent, 1=verbose telemetry feedback)

---

## Testing Strategy

### Unit Tests (`tests/test_ble_uart.py`)
```python
def test_ble_rx_buffer_accumulation():
    """Multiple RX events accumulate until newline."""

def test_ble_command_extraction():
    """Commands extracted correctly from buffer."""

def test_ble_buffer_overflow_protection():
    """Buffer doesn't exceed 128 bytes."""

def test_ble_partial_command_buffering():
    """Partial commands held in buffer, not processed."""
```

### Unit Tests (`tests/test_config.py`)
```python
def test_cv_validate_in_range():
    """Valid CV values accepted."""

def test_cv_validate_out_of_range():
    """Out-of-range values rejected with reason."""

def test_cv_validate_invalid_cv_number():
    """Invalid CV numbers rejected."""

def test_cv_validate_non_numeric():
    """Non-numeric values rejected."""

def test_cv_update_persists_to_flash():
    """Updated CV saved to config.json."""

def test_cv_update_atomic():
    """On error, old CV value preserved."""
```

### Integration Tests (`tests/test_main.py`)
```python
def test_ble_cv_command_flow():
    """Command: CV32=20.0 → CV table updated → telemetry ACK."""

def test_ble_multiple_commands_queued():
    """Multiple commands processed in FIFO order, one per loop."""

def test_ble_invalid_command_doesnt_break_loop():
    """Invalid command logged, loop continues."""

def test_ble_cv_update_takes_effect_immediately():
    """New CV value used in next control loop iteration."""

def test_performance_cv_command_processing():
    """CV command processing < 2ms."""
```

---

## Safety Considerations

### Input Validation
- ✅ Hardcoded bounds prevent unsafe values
- ✅ Parse errors logged, command rejected
- ✅ Non-numeric values rejected
- ✅ Out-of-range values rejected with reason

### Atomic Updates
- ✅ Old CV value preserved until new value validated
- ✅ Save to flash only after successful validation
- ✅ Update CV dict only after flash write succeeds

### Audit Trail
- ✅ Every successful CV update logged to event buffer
- ✅ Failed attempts logged with reason
- ✅ Event buffer persisted on emergency shutdown
- ✅ Operator can review what changed via BLE diagnostics

### Failsafe
- ✅ If BLE CV update corrupts config.json, factory defaults restored on next boot
- ✅ Watchdog thresholds always enforced (CV updates can't disable safety)
- ✅ CV85 allows administrator to disable BLE updates for security

### Attack Prevention
- ✅ Bounds checking prevents injection of malicious values
- ✅ RX queue limited to 16 commands (DoS protection)
- ✅ Command parsing doesn't use `eval()` (code injection impossible)
- ✅ Audit log allows forensic analysis if compromised

---

## Known Constraints

1. **128-byte RX buffer:** Long command strings not supported (not needed for CVs)
2. **No encryption:** BLE traffic unencrypted (model railway setting, acceptable risk)
3. **No authentication:** Any connected device can update CVs (CV85 disables for security)
4. **Single command per loop:** High-volume CV updates take up to 16 cycles = 320ms for 16 commands
5. **Float precision:** Some CVs truncated to nearest integer if needed (e.g., CV39 as int only)

---

## Implementation Checklist

### Code Changes
- [ ] Add `rx_queue` and `rx_buffer` to `BLE_UART` class
- [ ] Implement `on_ble_rx()` callback with buffer accumulation
- [ ] Implement `validate_and_update_cv()` in `config.py` with bounds matrix
- [ ] Add `process_ble_commands()` method to `Locomotive` class
- [ ] Call `process_ble_commands()` in main loop (after DCC, before physics)
- [ ] Add telemetry ACK/error fields to `ble_uart.py` `queue_telemetry()`
- [ ] Add CV85, CV86 to `CV.md` and `CV_DEFAULTS` in `config.py`

### Testing
- [ ] All BLE RX buffer tests passing
- [ ] All CV validation tests passing
- [ ] Integration tests showing command flow
- [ ] Performance test: CV processing < 2ms
- [ ] Manual test: Update CV via phone BLE app, verify takes effect

### Documentation
- [ ] Update `docs/FUNCTIONS.md` with BLE command format
- [ ] Update `docs/CV.md` with CV85, CV86 explanation
- [ ] Add troubleshooting section: "CV update rejected"
- [ ] Create `docs/implemented/ble-cv-update-technical.md`
- [ ] Create `docs/implemented/ble-cv-update-capabilities.md`

### Release
- [ ] Merge to main branch
- [ ] Tag v1.1.0
- [ ] Update CHANGELOG.md
- [ ] Update README.md with new feature badge

---

## Performance Budget

| Task | Time Budget | Notes |
|------|-------------|-------|
| BLE RX processing | < 1ms | Once per RX event (not guaranteed every cycle) |
| Command parsing | < 1ms | String operations, linear |
| CV validation | < 0.5ms | Bounds check only |
| CV dict update | < 0.1ms | Simple assignment |
| Flash write (`save_cvs`) | < 10ms | **Only once per successful command** |
| Per-loop overhead | < 2ms | Includes 1ms queue check |
| **Total per loop** | **< 2ms** | Well within 20ms budget (90% headroom) |
| **Per command (worst case)** | **10ms** | Due to flash write, spread across multiple commands |

---

## Future Enhancements (Post-Release)

1. **Encrypted BLE:** Add AES-128 encryption for authentication
2. **Batch CV updates:** Support multiple CVs in single command (e.g., `CV32=20,CV49=1200`)
3. **Conditional updates:** "If CV32 > 18, set CV41 to 80" type logic
4. **CV read-back:** Query current CV value via BLE (e.g., `?CV32`)
5. **Profile saving:** Save/restore entire CV sets (e.g., "race mode", "touring mode")

---

**Document Status:** Ready for implementation  
**Next Step:** Begin Phase 1 (BLE RX Infrastructure)

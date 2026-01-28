# Code Review & Improvement TODO List

**Date:** 28 January 2026  
**Status:** PLANNING  
**Priority:** High  
**Scope:** Complete codebase review for quality, testing, and performance improvements

---

## � CRITICAL: Emergency Shutdown Procedure (VERIFIED ✅)

**The correct safety sequence for emergency shutdown is:**

1. **Turn off heaters** (Instant - <10ms)
   - Prevents stay-alive capacitor from being drained by thermal load
   - Prevents boiler pressure from rising during crash/power loss
   - Protects 1F capacitor bank

2. **Move regulator to whistle position** (5 seconds)
   - Reduces boiler pressure safely by venting steam
   - Creates audible alert if locomotive unattended
   - Gives time for pressure to stabilize

3. **Write event log to flash** (Very fast - <100ms)
   - Saves telemetry and error data before power drains
   - Enables post-mortem analysis of failure cause
   - File write errors are silently ignored (shutdown continues)

4. **Move regulator to fully closed position** (500ms)
   - MUST complete before power drains to TinyPICO
   - Prevents uncontrolled steam release
   - Allows servo to enter safe neutral state with power

5. **Cut servo power** (Instant)
   - Disables servo PWM signal
   - Allows ESP32 to enter deep sleep safely

6. **Enter deep sleep** (Power off)
   - Prevents restart without manual power cycle
   - Requires user intervention to recover
   - Protects against repeated thermal cycling damage

**Status:** ✅ Implemented in [app/main.py#L95](app/main.py#L95)

### Exception: DCC E-STOP Command (Operator Override)

The **ONLY exception** to the full shutdown sequence is when a DCC E-STOP command is received from the command station. In this case:

1. **Move regulator to fully closed position** (Instant)
   - Rapid regulator closure via emergency mode bypass
   - Operator retains control (locomotive may coast)
   - Locomotive stops motion but NOT entering deep sleep

**Why this exception:**
- E-STOP is an operator command (not a fault)
- Command station still communicating (control maintained)
- Operator may resume if E-STOP was accidental
- No need for full emergency shutdown ritual

**Implementation:**
- `die("USER_ESTOP", force_close_only=True)` called from main loop
- Bypasses heater shutdown, log save, and deep sleep
- Only closes regulator instantly for immediate stop
- E-STOP flag added to DCCDecoder class (e_stop attribute)
- Main loop checks E-STOP before watchdog (operator priority)

**Status:** ✅ Implemented in [app/main.py#L95-L155](app/main.py#L95), [app/dcc_decoder.py#L60](app/dcc_decoder.py#L60), [tests/test_main.py#L305](tests/test_main.py#L305)

---

## �🔍 Code Quality Issues (Priority: HIGH)

### 1. Fix Remaining 11 Test Failures
**Estimated Effort:** 6-8 hours
**Impact:** Achieve 100% test pass rate (105/105)

- [ ] **test_jitter_sleep_mode** - Time mocking issue with 2-second timeout (test_actuators.py:57)
  - Problem: MockTime integration with sleep mode detection
  - Solution: Refactor time mocking to properly simulate timeout elapsed
  
- [ ] **test_uart_service_uuids** - BLE UUID import error (test_ble_uart.py)
  - Problem: ModuleNotFoundError for BLE UUID handling
  - Solution: Mock struct module for UUID validation
  
- [ ] **test_no_deeply_nested_code** - Nesting depth validation (test_complexity.py:87)
  - Problem: Some functions exceed 4-level nesting limit
  - Solution: Refactor nested conditionals into helper methods
  
- [ ] **test_decoder_initialization_long_address** - DCC address parsing (test_dcc_decoder.py)
  - Problem: 14-bit long address handling not working correctly
  - Solution: Fix address decoding logic in DCCDecoder.__init__()
  
- [ ] **test_function_command_whistle** - DCC function decoding (test_dcc_decoder.py)
  - Problem: Function group decoding not setting whistle flag correctly
  - Solution: Review bit masking in _decode_packet()
  
- [ ] **test_function_command_whistle_off** - DCC function off state (test_dcc_decoder.py)
  - Problem: Whistle off state not being tracked
  - Solution: Add state tracking for function off commands
  
- [ ] **test_control_loop_watchdog_check_called** - Watchdog verification (test_main.py)
  - Problem: Mock assertion failure on watchdog.check() call
  - Solution: Fix mock call recording in control loop
  
- [ ] **test_memory_garbage_collection_threshold** - GC threshold mocking (test_main.py:357)
  - Problem: MockTime doesn't have datetime/struct_time attributes
  - Solution: Enhance MockTime class with datetime simulation
  
- [ ] **test_watchdog_power_loss** - Power timeout logic (test_safety.py:166)
  - Problem: die() not being called on power timeout
  - Solution: Debug watchdog timeout timer in safety.py
  
- [ ] **test_watchdog_dcc_signal_loss** - DCC signal timeout (test_safety.py:205)
  - Problem: die() not being called on DCC signal loss timeout
  - Solution: Debug DCC timeout timer logic
  
- [ ] **test_watchdog_multiple_simultaneous_faults** - Multi-fault handling (test_safety.py:260)
  - Problem: Multiple die() calls instead of single call
  - Solution: Add die() guard to prevent multiple emergency shutdowns

---

## 📊 Test Coverage Improvements (Priority: HIGH)

### 2. Fix Test Coverage Infrastructure
**Estimated Effort:** 2-3 hours
**Impact:** Enable accurate coverage reporting

- [ ] **Fix MockTime class** - Causes coverage.py crashes
  - Add `struct_time` attribute to MockTime
  - Implement datetime compatibility for coverage.py
  - Allow proper time.time() mocking
  - File: tests/conftest.py:65

- [ ] **Add coverage.py configuration**
  - Create `.coveragerc` with proper source settings
  - Exclude conftest.py from coverage (mock infrastructure)
  - Set coverage threshold to 85% minimum
  - File: Create `.coveragerc`

- [ ] **Achieve 85%+ line coverage**
  - Current coverage: Unknown (coverage.py broken)
  - Target: 85% minimum (safety-critical standard)
  - Failing tests prevent accurate measurement

---

## 🔧 Code Refactoring (Priority: MEDIUM)

### 3. Reduce Nesting Depth in Complex Functions
**Estimated Effort:** 4-6 hours
**Impact:** Improve code readability, pass nesting depth test

- [ ] **app/main.py** - Main control loop (line 155)
  - Current nesting: 5+ levels in run() function
  - Solution: Extract sensor reading, watchdog check, actuator updates into helper methods
  - Expected: Reduce to 3-4 levels

- [ ] **app/dcc_decoder.py** - Packet decoding (line 103)
  - Current nesting: 5+ levels in _decode_packet()
  - Solution: Extract address filtering, speed command, function command into separate methods
  - Expected: Reduce to 3 levels

- [ ] **app/safety.py** - Watchdog check (line 85)
  - Current nesting: 4+ levels in check() method
  - Solution: Extract thermal check, timeout check into separate methods
  - Expected: Reduce to 2 levels

---

## 📝 Documentation Improvements (Priority: MEDIUM)

### 4. Complete API Documentation
**Estimated Effort:** 3-4 hours
**Impact:** User-facing documentation completeness

- [ ] **Update docs/FUNCTIONS.md**
  - Add all 9 module functions with signatures
  - Add parameter descriptions with valid ranges
  - Add return value descriptions
  - Add exception documentation
  - Current: Incomplete, only shows function group mapping

- [ ] **Create docs/DEPLOYMENT.md**
  - Add step-by-step deployment instructions to TinyPICO
  - Include ampy commands for file upload
  - Include boot.py setup instructions
  - Include recovery procedures

- [ ] **Create docs/TROUBLESHOOTING.md**
  - Common issues and solutions
  - Debug techniques using BLE telemetry
  - Memory usage profiling guide
  - Thermal monitoring guide

- [ ] **Update README.md**
  - Add quick start guide
  - Add hardware requirements (TinyPICO, servo, pressure sensor, etc.)
  - Add wiring diagram reference
  - Add calibration procedures

---

## 🚀 Performance Optimizations (Priority: MEDIUM)

### 5. Performance Profiling & Optimization
**Estimated Effort:** 4-5 hours
**Impact:** Verify 50Hz control loop timing, identify bottlenecks

- [ ] **Profile 50Hz control loop timing**
  - Add timing instrumentation to main.py run() loop
  - Measure per-stage execution time:
    - Sensor reading (~30ms expected)
    - Physics calculation (~2ms expected)
    - Watchdog check (~1ms expected)
    - Servo update (~1ms expected)
    - BLE telemetry (~5ms every 1s)
  - File: app/main.py:155

- [ ] **Optimize memory usage**
  - Profile GC pressure during normal operation
  - Current GC threshold: 60KB
  - Test with extended operation (1+ hour)
  - Add memory usage telemetry to BLE output

- [ ] **Optimize DCC signal decoding**
  - ISR execution time <10µs target
  - Current implementation uses Pin.irq() callback
  - Verify timing meets NMRA requirements

---

## 🧪 Test Enhancement (Priority: MEDIUM)

### 6. Expand Test Coverage for Edge Cases
**Estimated Effort:** 3-4 hours
**Impact:** Improve robustness

- [ ] **Add hardware stress tests**
  - Rapid temperature changes (thermal shock)
  - Rapid pressure changes
  - Extended high-pressure operation
  - Extended low-pressure operation

- [ ] **Add DCC edge case tests**
  - Out-of-order packet recovery
  - Checksum validation edge cases
  - Address filtering with broadcast packets
  - Function group timing requirements

- [ ] **Add safety system edge cases**
  - Multiple simultaneous thermal faults
  - Intermittent DCC signal (packet loss)
  - Intermittent power (brownout)
  - Sensor calibration recovery

---

## 🔐 Safety Audit (Priority: HIGH)

### 7. Complete Safety-Critical Verification
**Estimated Effort:** 5-7 hours
**Impact:** Verify safety properties

- [x] **Verify emergency shutdown sequence** ✅ VERIFIED
  - Correct sequence: Heater off → Whistle → Log save → Regulator close → Sleep
  - Heater cutoff (<10ms) - prevents stay-alive capacitor drain & pressure rise
  - Whistle position (5s) - reduces boiler pressure + audible alert if unattended
  - Log save (<100ms) - preserves telemetry, errors ignored if blocked
  - Regulator full close (500ms) - before power drains, prevent drift
  - Implementation: [app/main.py#L95](app/main.py#L95)

- [ ] **Verify thermal safety limits**
  - All thresholds <= failure temperatures
  - CV41 (logic): 75°C default - is TinyPICO max 85°C?
  - CV42 (boiler): 110°C default - appropriate for scale?
  - CV43 (superheater): 250°C default - verify steam pipe rating

- [ ] **Verify power/signal timeout logic**
  - CV44 (DCC): 20 * 100ms = 2000ms timeout
  - CV45 (power): 8 * 100ms = 800ms timeout
  - Hysteresis prevents oscillation during power dips

- [ ] **Verify servo safety**
  - Slew rate CV49 = 1000ms - allows smooth motion
  - Emergency mode bypass works (tested?)
  - Neutral position (CV46) always reachable

---

## 📦 Build & Release (Priority: LOW)

### 8. Prepare Production Release
**Estimated Effort:** 2-3 hours
**Impact:** Professional distribution

- [ ] **Create version management**
  - Add semantic versioning to app/__init__.py
  - Add version to BLE telemetry output
  - Create CHANGELOG.md for release notes

- [ ] **Create firmware packaging**
  - Create app.zip for distribution
  - Include deployment instructions
  - Include recovery procedures

- [ ] **Create CI/CD pipeline** (GitHub Actions)
  - Run pylint on push (fail-under=9.9)
  - Run pytest (fail on <90% pass)
  - Generate test coverage report
  - Publish release artifacts

---

## 🎯 Current Status Summary

| Category | Status | Score |
|----------|--------|-------|
| **Code Quality** | ✅ Excellent | 10.00/10 |
| **Test Pass Rate** | ⚠️ Good | 90% (94/105) |
| **Type Hints** | ✅ Complete | 100% |
| **Docstrings** | ✅ Complete | 100% |
| **Test Coverage** | ❌ Broken | N/A |
| **Documentation** | ⚠️ Partial | 70% |
| **Performance** | ❓ Untested | N/A |
| **Safety Audit** | ⚠️ Pending | N/A |

---

## Recommended Work Order

**Phase 1: Quality & Testing (Week 1)**
1. Fix MockTime class and test coverage infrastructure (2-3 hrs)
2. Fix 11 failing tests (6-8 hrs)
3. Achieve 85%+ code coverage (2 hrs)
4. Result: 100% test pass rate, full coverage visibility

**Phase 2: Code Quality (Week 2)**
1. Refactor nested code (4-6 hrs)
2. Complete safety audit (5-7 hrs)
3. Result: Verified safety properties, improved readability

**Phase 3: Documentation (Week 3)**
1. Complete API documentation (3-4 hrs)
2. Create deployment & troubleshooting guides (3-4 hrs)
3. Result: Professional documentation suite

**Phase 4: Polish & Release (Week 4)**
1. Performance profiling (4-5 hrs)
2. Release packaging (2-3 hrs)
3. Result: Production-ready release

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Safety audit finds critical issue | Medium | High | Fix immediately before deployment |
| Coverage measurement requires refactor | Low | Medium | Start early, have rollback plan |
| Performance fails 50Hz target | Low | High | Profile early, may need hardware upgrade |
| Test failures due to environment issues | Medium | Low | Isolate and document all test dependencies |

---

## Decision Points

**Decision 1:** Should we increase test pass rate to 100% or accept 90%?
- Recommendation: **100%** - Safety-critical systems should have zero known failures
- Impact: Requires fixing all 11 tests

**Decision 2:** Should we optimize code before or after passing all tests?
- Recommendation: **After** - Tests verify correctness, refactoring can break things
- Order: Fix tests → Refactor → Optimize

**Decision 3:** Should CI/CD be mandatory or optional?
- Recommendation: **Mandatory** - Prevents regression on future changes
- Tools: GitHub Actions with pylint + pytest


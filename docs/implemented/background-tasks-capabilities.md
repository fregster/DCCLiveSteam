# Background Task Manager

## What It Is

A collection of five smart helpers that keep your locomotive's computer responsive by doing slow jobs in the background instead of freezing while waiting for them to finish.

Think of it like a restaurant kitchen: The head chef (main control loop) focuses on cooking orders fast, while prep cooks (background tasks) handle slow jobs like washing dishes, taking inventory, and restocking supplies. The chef never stops cooking to wait for dishes.

## What It Does

The Background Task Manager handles five types of slow operations:

1. **USB Serial Messages** - Prints diagnostic messages to your computer without freezing
2. **File Writing** - Saves emergency logs and configuration files without blocking
3. **Memory Cleanup** - Garbage collection runs automatically when memory gets low
4. **Sensor Reading** - Temperature/pressure readings cached so control loop doesn't wait
5. **Wheel Encoder** - Tracks locomotive speed using interrupts (no polling needed)

**Key Benefit:** Your locomotive's control system runs at a steady 50 times per second (50Hz), even when writing files or reading sensors. This keeps the regulator valve responding smoothly.

## Why It Matters

**Before Background Tasks:**
- Reading all sensors: ~30ms (milliseconds)
- Printing to USB: ~2-5ms
- Saving a file: ~10-50ms
- **Total worst-case: 96ms (can only run 10 times per second!)**

**After Background Tasks:**
- Reading cached sensors: ~1ms
- Queueing a print: ~0.5ms
- Queueing a file save: ~0.5ms
- **Total: ~9ms (runs 50 times per second with room to spare)**

**Real Impact:**
- Smoother regulator movement (no jerky motion during file saves)
- Faster watchdog response (checks safety limits 50 times/second)
- More reliable emergency logging (black box recorder never misses events)
- Longer flash memory lifespan (rate-limited writes prevent wear)

## How to Use It

**You don't need to do anything special.** The background tasks are built into the system and work automatically. However, understanding how they work helps with troubleshooting.

### 1. USB Serial Messages (Telemetry)

**What It Does:** Prints diagnostic messages to your computer via USB without freezing the control loop.

**How It Works:**
- Messages queue up (up to 10 messages)
- Prints happen in background (max 20 messages/second)
- If queue fills, oldest messages drop (newer messages preserved)

**Example Messages:**
```
Speed: 35.2 cm/s | Target: 40.0 cm/s | Regulator: 45%
Boiler: 95.0°C | Superheater: 210.0°C | Logic: 45.0°C
Track Voltage: 14.0 V | Pressure: 345 kPa (50.0 PSI)
```

**Troubleshooting:**
- **Missing messages:** Queue full (system busy, messages dropped)
- **Delayed messages:** Rate limiting (max 20/second)
- **No messages:** USB cable disconnected or serial monitor not running

### 2. File Writing (Logs & Configuration)

**What It Does:** Saves files without freezing the control loop (emergency logs, CV updates).

**How It Works:**
- File writes queue up (up to 5 writes)
- Emergency logs ALWAYS prioritised over routine saves
- Writes happen in background (max 10 writes/second)

**Priority Levels:**
- **HIGH Priority:** Emergency logs (black box recorder, safety shutdowns)
- **LOW Priority:** Routine saves (CV configuration updates)

**Example Operations:**
```
# Emergency log (saved immediately, never dropped)
System E-STOP triggered at 14:32:15
Black box recorder saved: error_log.json (Priority: HIGH)

# CV update (saved when queue has room, may be delayed)
CV 42 changed: 110 → 105 (User BLE command)
Configuration saved: config.json (Priority: LOW)
```

**Troubleshooting:**
- **CV changes not saving:** Queue full (wait a few seconds, try again)
- **Emergency log missing:** Hardware failure (flash memory corrupted)
- **Slow saves:** Rate limiting (max 10 writes/second protects flash)

### 3. Memory Cleanup (Garbage Collection)

**What It Does:** Automatically frees up unused memory when it gets low.

**How It Works:**
- Memory checked every loop iteration (~50 times/second)
- Cleanup runs when free memory < 60KB
- Critical cleanup forces immediate collection if < 5KB

**Memory Thresholds:**
- **> 60KB free:** No action (plenty of memory)
- **5KB - 60KB free:** Schedule cleanup (if 1 second elapsed since last)
- **< 5KB free:** Force immediate cleanup (override rate limit)

**Example Behaviour:**
```
Normal operation: 80KB free → No cleanup needed
Busy operation: 45KB free → Cleanup scheduled (next background cycle)
Critical: 3KB free → Cleanup forced immediately (prevent crash)
```

**Troubleshooting:**
- **Frequent cleanups:** Memory leak (object not released)
- **Heap exhaustion:** Cleanup can't keep up (reduce object creation)
- **Crashes:** Critical threshold hit too frequently (code bug)

### 4. Sensor Reading (Temperature, Pressure, Voltage)

**What It Does:** Reads sensors in background, control loop uses cached values.

**How It Works:**
- Sensors read every 100ms (10 times/second)
- Control loop accesses cached values (<1ms, no waiting)
- Cache automatically refreshes when stale

**Cache Behaviour:**
- **Fresh (<100ms old):** Return cached value (no ADC read)
- **Stale (>100ms old):** Return cached + schedule refresh
- **Refresh:** Background reads all sensors (~30ms total)

**Example Timing:**
```
Time 0ms:   Read sensors (30ms background)
Time 50ms:  Control loop uses cached values (<1ms)
Time 100ms: Cache stale, refresh scheduled
Time 105ms: Control loop uses cached values (<1ms)
Time 110ms: Background refresh (30ms background)
```

**Troubleshooting:**
- **Stale sensor readings:** Cache refresh failing (sensor disconnected?)
- **Erratic temperatures:** Cache validity too long (reduce from 100ms)
- **Thermal shutdown:** Sensor failure returns 999.9°C (triggers watchdog)

### 5. Wheel Encoder (Speed Tracking)

**What It Does:** Tracks wheel rotation using hardware interrupts (no polling overhead).

**How It Works:**
- Encoder pulse triggers interrupt (automatic hardware response)
- Interrupt handler increments counter (<1µs, faster than blinking)
- Control loop calculates velocity from counter delta

**Velocity Calculation:**
```
Delta = Current Count - Previous Count
Elapsed = Current Time - Previous Time
Velocity = (Delta × Wheel Circumference) / Elapsed
```

**Example Operation:**
```
Encoder pulse → IRQ triggers → Counter++
Main loop (50Hz): Read counter, calculate velocity
Velocity: 35.2 cm/s (wheel turning 25.4mm circumference @ 138 pulses/second)
```

**Troubleshooting:**
- **Velocity = 0:** Encoder not triggering (wiring issue, magnet misaligned)
- **Erratic velocity:** Mechanical noise (magnet wobbling, sensor bounce)
- **No velocity updates:** IRQ not firing (pin configuration wrong)

## Real-World Example

**Scenario:** Locomotive approaching station, whistle blowing, BLE command received to reduce boiler limit (CV42).

**Without Background Tasks (OLD):**
```
Time 0ms:   Read sensors (30ms) ← BLOCKING
Time 30ms:  Print telemetry (5ms) ← BLOCKING
Time 35ms:  Control logic (5ms)
Time 40ms:  Save CV file (50ms) ← BLOCKING
Time 90ms:  Next loop starts (90ms total = 11Hz, jittery regulator)
```

**With Background Tasks (NEW):**
```
Time 0ms:   Read cached sensors (1ms) ← NON-BLOCKING
Time 1ms:   Queue telemetry print (0.5ms) ← NON-BLOCKING
Time 1.5ms: Control logic (5ms)
Time 6.5ms: Queue CV file save (0.5ms) ← NON-BLOCKING
Time 7ms:   Process background tasks (2ms)
Time 9ms:   Sleep until next frame
Time 20ms:  Next loop starts (20ms total = 50Hz, smooth)

Background processing (parallel):
Time 10ms:  Print telemetry to USB (5ms, doesn't block control)
Time 50ms:  Write CV file to flash (50ms, doesn't block control)
```

**Result:**
- Control loop maintains 50Hz (smooth regulator movement)
- Telemetry still printed (just queued first)
- CV file still saved (just queued first)
- Watchdog checks run 50 times/second (was 11 times/second)

## Troubleshooting

### Problem: Telemetry messages missing

**Symptoms:** USB serial monitor shows gaps in messages, some data missing

**Causes:**
1. Queue overflow (more than 10 messages queued)
2. Rate limiting (printing faster than 20 messages/second)

**Solutions:**
- Reduce telemetry frequency (print every N loops instead of every loop)
- Increase queue size (requires code change)
- Check USB cable connection

---

### Problem: CV changes not saving

**Symptoms:** Configuration changes lost after reboot

**Causes:**
1. File queue full (more than 5 writes queued)
2. Flash memory failure (hardware issue)
3. Power loss before write completes

**Solutions:**
- Wait 1-2 seconds after CV change (allow queue to drain)
- Check flash memory health (test file writes)
- Use HIGH priority for critical CV changes

---

### Problem: Sensor readings stale

**Symptoms:** Temperature/pressure values don't update for >100ms

**Causes:**
1. Sensor disconnected (ADC read failing)
2. Cache refresh failing (background task blocked)
3. High system load (background processing delayed)

**Solutions:**
- Check sensor wiring (ADC pins connected?)
- Reduce background task frequency (more CPU for cache refresh)
- Monitor cache refresh timing (add debug logging)

---

### Problem: Velocity erratic

**Symptoms:** Speed readings jump around, not smooth

**Causes:**
1. Encoder mechanical noise (magnet wobbling)
2. IRQ debouncing needed (electrical bounce)
3. Wheel slipping (actual velocity changing)

**Solutions:**
- Check encoder alignment (magnet-sensor gap <3mm)
- Add capacitor to encoder signal (filter electrical noise)
- Verify wheel contact with track (no slipping)

---

### Problem: Memory exhaustion

**Symptoms:** System crashes with "MemoryError", frequent GC

**Causes:**
1. Memory leak (object not released)
2. Excessive object creation (strings, lists)
3. GC rate limit too long (1 second delay allows heap growth)

**Solutions:**
- Reduce object creation in main loop (reuse objects)
- Force GC manually (gc.collect() after big operations)
- Lower GC threshold (trigger cleanup earlier than 60KB)

## Safety Notes

**What's Protected:**
- ✅ Control loop timing (guaranteed <20ms response)
- ✅ Emergency logs (HIGH priority, never dropped)
- ✅ Flash lifespan (rate-limited writes prevent wear)
- ✅ Memory stability (automatic GC prevents exhaustion)

**What's NOT Protected:**
- ❌ Telemetry completeness (messages may drop if queue full)
- ❌ CV save timing (LOW priority, may be delayed)
- ❌ Sensor precision (100ms cache means 10Hz sampling)

**Warnings:**
- **Queue overflow:** If queues full, LOW priority operations dropped
- **Cache staleness:** Sensors sampled at 10Hz, not 50Hz (thermal events <100ms may be missed)
- **Flash wear:** Continuous high-priority writes exhaust flash lifespan
- **IRQ safety:** Encoder IRQ must be <1µs (no complex logic)

**When to Worry:**
- Frequent queue overflow (system overloaded)
- GC running every second (memory leak)
- Cache never refreshing (sensor failure)
- Velocity stuck at zero (encoder disconnected)

**When NOT to Worry:**
- Occasional message drops (telemetry not safety-critical)
- Delayed CV saves (eventual consistency acceptable)
- 100ms sensor lag (thermal systems slow-changing)
- Single GC per 10 seconds (normal memory churn)

---

**For technical details, see:** [background-tasks-technical.md](background-tasks-technical.md)

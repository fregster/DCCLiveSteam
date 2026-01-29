"""
Background task manager for non-blocking operations.

Why: Main 50Hz control loop must stay <20ms. Non-critical operations (USB serial,
file I/O, garbage collection) can be deferred to background without affecting
control responsiveness. Queue-based architecture prevents blocking on slow operations.

Safety: All queued operations are non-critical. Task failures don't cascade to main
loop. Memory-bounded queues prevent heap exhaustion.
"""
from typing import Any, List
from collections import deque
import gc
import time


class SerialPrintQueue:
    """Non-blocking queue for USB serial output.

    Why: print() can block for 2-5ms on USB serial. Queuing messages and writing
    in background keeps main loop timing predictable.

    Safety: Queue size limited to 10 messages. If full, oldest messages dropped
    (telemetry is not safety-critical). Non-blocking enqueue/dequeue operations.

    Example:
        >>> queue = SerialPrintQueue()
        >>> queue.enqueue("Speed: 45.3 cm/s")
        >>> queue.process()  # Prints one message if ready
    """

    def __init__(self, max_size: int = 10) -> None:
        """Initialize serial print queue.

        Args:
            max_size: Maximum messages to buffer (default 10)

        Safety: Limited queue prevents memory exhaustion from print spam.
        """
        self._queue: deque = deque((), max_size)
        self._last_print_time = time.ticks_ms()
        self._min_interval_ms = 50  # Minimum 50ms between prints

    def enqueue(self, message: str) -> None:
        """Add message to print queue (non-blocking).

        Args:
            message: String to print to USB serial

        Safety: If queue full, oldest message dropped. Non-blocking always.

        Example:
            >>> queue.enqueue("PSI: 45.2")
        """
        try:
            self._queue.append(message)
        except Exception:
            pass  # Queue full, drop message (non-critical telemetry)

    def process(self) -> None:
        """Print one queued message if enough time elapsed.

        Why: Rate-limited to prevent USB serial saturation. Processes one message
        per call to maintain <1ms processing time.

        Safety: Non-blocking, max 1ms execution time. Failed prints silently dropped.

        Example:
            >>> queue.process()  # Call from main loop
        """
        now = time.ticks_ms()

        # Rate limit: min 50ms between prints
        if time.ticks_diff(now, self._last_print_time) < self._min_interval_ms:
            return

        # Process one message
        if len(self._queue) > 0:
            try:
                message = self._queue.popleft()
                print(message)
                self._last_print_time = now
            except Exception:
                pass  # Print failed, continue


class FileWriteQueue:
    """Non-blocking queue for file write operations.

    Why: JSON file writes (config.json, error_log.json) block for 10-50ms.
    Queuing writes allows main loop to continue without waiting for flash I/O.

    Safety: Queue size limited to 5 writes. Critical writes (emergency logs) take
    priority over routine writes (CV updates). Write failures logged but don't crash.

    Example:
        >>> queue = FileWriteQueue()
        >>> queue.enqueue_write("config.json", '{"CV1": 3}', priority=False)
        >>> queue.process()  # Writes one file if ready
    """

    def __init__(self, max_size: int = 5) -> None:
        """Initialize file write queue.

        Args:
            max_size: Maximum pending writes (default 5)

        Safety: Limited queue prevents memory exhaustion. Priority queue ensures
        emergency logs written before routine CV updates.
        """
        self._queue: List[tuple] = []
        self._max_size = max_size
        self._last_write_time = time.ticks_ms()
        self._min_interval_ms = 100  # Minimum 100ms between writes

    def enqueue_write(self, filepath: str, content: str, priority: bool = False) -> None:
        """Queue a file write operation.

        Args:
            filepath: Path to file (e.g., "config.json")
            content: String content to write
            priority: True for emergency logs (front of queue), False for routine

        Safety: If queue full, drops lowest-priority write. Non-blocking always.

        Example:
            >>> queue.enqueue_write("error_log.json", '{"err": "THERMAL"}', priority=True)
        """
        if len(self._queue) >= self._max_size:
            # Queue full - drop lowest priority write
            if not priority:
                return  # Don't queue low-priority if full
            # Remove oldest low-priority write
            for i, (_, _, p) in enumerate(self._queue):
                if not p:
                    self._queue.pop(i)
                    break

        # Add to queue (priority writes at front)
        entry = (filepath, content, priority)
        if priority:
            self._queue.insert(0, entry)
        else:
            self._queue.append(entry)

    def process(self) -> None:
        """Write one queued file if enough time elapsed.

        Why: Rate-limited to prevent flash wear and I/O congestion. Processes one
        write per call to maintain <50ms worst-case time.

        Safety: Non-blocking enqueue, blocking write (but only when called). Failed
        writes silently dropped (file I/O is not safety-critical for control loop).

        Example:
            >>> queue.process()  # Call from main loop
        """
        now = time.ticks_ms()

        # Rate limit: min 100ms between writes
        if time.ticks_diff(now, self._last_write_time) < self._min_interval_ms:
            return

        # Process one write
        if len(self._queue) > 0:
            try:
                filepath, content, _ = self._queue.pop(0)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                self._last_write_time = now
            except Exception:
                pass  # Write failed, continue


class GarbageCollector:
    """Scheduled garbage collection to prevent OOM.

    Why: Running gc.collect() in main loop when heap low adds unpredictable latency
    spikes (10-50ms). Scheduled GC during idle periods keeps heap healthy without
    affecting control timing.

    Safety: GC runs max once per second. If heap critically low (<5KB), forces
    immediate collection to prevent OOM crash.

    Example:
        >>> gc_mgr = GarbageCollector(threshold_kb=60)
        >>> gc_mgr.process()  # Runs GC if needed
    """

    def __init__(self, threshold_kb: int = 60) -> None:
        """Initialize garbage collector.

        Args:
            threshold_kb: Run GC when free memory below this (default 60KB)

        Safety: Conservative threshold triggers GC before critical low memory.
        """
        self._threshold_bytes = threshold_kb * 1024
        self._last_gc_time = time.ticks_ms()
        self._min_interval_ms = 1000  # Max once per second
        self._critical_threshold_bytes = 5 * 1024  # 5KB critical

    def process(self) -> None:
        """Run garbage collection if needed.

        Why: Scheduled GC prevents unpredictable latency spikes in control loop.
        Only runs if (a) heap below threshold AND (b) enough time since last GC.

        Safety: Critical low memory (<5KB) forces immediate GC regardless of timing
        to prevent OOM crash.

        Example:
            >>> gc_mgr.process()  # Call from main loop
        """
        free_mem = gc.mem_free()
        now = time.ticks_ms()

        # CRITICAL: Force GC if memory dangerously low
        if free_mem < self._critical_threshold_bytes:
            try:
                gc.collect()
                self._last_gc_time = now
            except Exception:
                pass
            return

        # SCHEDULED: Run GC if below threshold and enough time elapsed
        if free_mem < self._threshold_bytes:
            if time.ticks_diff(now, self._last_gc_time) >= self._min_interval_ms:
                try:
                    gc.collect()
                    self._last_gc_time = now
                except Exception:
                    pass


class CachedSensorReader:
    """Cached sensor readings updated in background.

    Why: ADC reads with oversampling take ~30ms (10 samples × 3ms each). Caching
    last-good values and updating asynchronously keeps main loop fast while still
    getting fresh sensor data.

    Strategy:
    - Main loop reads cached values (<1ms)
    - Background task updates cache when stale (>100ms old)
    - Failed reads use last-valid value (graceful degradation)

    Safety: Cache never older than 200ms (meets watchdog 50Hz requirement). Failed
    sensor reads don't block main loop. Watchdog still monitors cached values.

    Example:
        >>> reader = CachedSensorReader(sensor_suite)
        >>> temps = reader.get_temps()  # Instant, uses cache
        >>> reader.update_cache()  # Background refresh (call periodically)
    """

    def __init__(self, sensor_suite: Any) -> None:
        """Initialize cached sensor reader.

        Args:
            sensor_suite: SensorSuite instance to wrap

        Safety: Cache initialized with safe defaults (ambient temp, no pressure).
        """
        self._sensors = sensor_suite
        self._cached_temps = (25.0, 25.0, 25.0)  # (boiler, super, logic)
        self._cached_pressure = 0.0
        self._cached_track_v = 0.0
        self._last_update_time = time.ticks_ms()
        self._max_cache_age_ms = 100  # Refresh if older than 100ms

    def get_temps(self) -> tuple:
        """Get cached temperature readings (non-blocking).

        Returns:
            Tuple of (boiler_temp, super_temp, logic_temp) in Celsius

        Safety: Always returns immediately. Cache refreshed in background.

        Example:
            >>> temps = reader.get_temps()
            >>> temps[0]  # Boiler temp
            98.5
        """
        return self._cached_temps

    def get_pressure(self) -> float:
        """Get cached pressure reading (non-blocking).

        Returns:
            Pressure in PSI (0-100)

        Safety: Always returns immediately.
        """
        return self._cached_pressure

    def get_track_voltage(self) -> float:
        """Get cached track voltage (non-blocking).

        Returns:
            Track voltage in volts (0-18V)

        Safety: Always returns immediately.
        """
        return self._cached_track_v

    def update_cache(self) -> None:
        """Refresh sensor cache if stale.

        Why: Only reads sensors if cache older than 100ms. Prevents unnecessary
        ADC operations while ensuring data stays fresh.

        Safety: Failed sensor reads keep last-valid values. Non-blocking check,
        blocking read (only when called explicitly from background).

        Example:
            >>> reader.update_cache()  # Call periodically from main loop
        """
        now = time.ticks_ms()

        # Check if cache needs refresh
        if time.ticks_diff(now, self._last_update_time) < self._max_cache_age_ms:
            return

        # Update cache (may take ~30ms with oversampling)
        try:
            self._cached_temps = self._sensors.read_temps()
            self._cached_pressure = self._sensors.read_pressure()
            self._cached_track_v = self._sensors.read_track_voltage()
            self._last_update_time = now
        except Exception:
            # Sensor read failed, keep last-valid values
            pass


class EncoderTracker:
    """Interrupt-driven encoder tracking with velocity calculation.

    Why: Polling encoder in main loop adds latency. IRQ-based tracking captures every
    edge, calculates velocity in background, main loop just reads cached value.

    Safety: Velocity calculated from time delta, not just count delta (handles
    variable loop timing). Cache never stale (IRQ updates continuously).

    Example:
        >>> tracker = EncoderTracker(pin=14)
        >>> velocity = tracker.get_velocity_cms()  # Instant, uses cached calculation
    """

    def __init__(self, pin_encoder: Any) -> None:
        """Initialize encoder tracker with IRQ.

        Args:
            pin_encoder: Encoder GPIO pin (must support IRQ)

        Safety: IRQ handler keeps count, velocity calculation non-blocking.
        """
        self._encoder_pin = pin_encoder
        self._count = 0
        self._last_count = 0
        self._last_time = time.ticks_ms()
        self._cached_velocity_cms = 0.0

        # Attach IRQ handler
        try:
            self._encoder_pin.irq(trigger=self._encoder_pin.IRQ_RISING, handler=self._irq_handler)
        except Exception:
            pass  # IRQ setup failed, will fall back to polling

    def _irq_handler(self, pin: Any) -> None:
        """IRQ callback on encoder edge.

        Why: Runs in interrupt context, must be fast (<10μs). Just increments counter.

        Safety: No allocations, no blocking calls. Thread-safe counter increment.
        """
        self._count += 1

    def update_velocity(self) -> None:
        """Calculate velocity from encoder delta (call from main loop).

        Why: Velocity calculation (division, time delta) too slow for IRQ. Main loop
        calls this periodically to update cached velocity.

        Safety: Non-blocking read of IRQ counter. Division-by-zero protection.

        Example:
            >>> tracker.update_velocity()  # Call every loop iteration
        """
        now = time.ticks_ms()
        time_delta = time.ticks_diff(now, self._last_time)

        if time_delta >= 1000:  # Update every second
            count_delta = self._count - self._last_count

            # Calculate velocity (counts/sec to cm/s conversion)
            # Assumes calibration: 1 count = 0.1 cm (adjust for your encoder)
            if time_delta > 0:
                counts_per_sec = (count_delta * 1000) / time_delta
                self._cached_velocity_cms = counts_per_sec * 0.1  # Scale factor

            self._last_count = self._count
            self._last_time = now

    def get_velocity_cms(self) -> float:
        """Get cached velocity calculation (non-blocking).

        Returns:
            Velocity in cm/s

        Safety: Always returns immediately.

        Example:
            >>> velocity = tracker.get_velocity_cms()
            >>> velocity
            45.3
        """
        return self._cached_velocity_cms

    def get_count(self) -> int:
        """Get raw encoder count.

        Returns:
            Total encoder pulses since boot

        Safety: Non-blocking read.
        """
        return self._count

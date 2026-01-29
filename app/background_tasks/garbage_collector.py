"""
Scheduled garbage collection to prevent OOM.
"""
import gc
import time

class GarbageCollector:
    """
    Scheduled garbage collection to prevent OOM.

    Why:
        Running gc.collect() in main loop when heap low adds unpredictable latency
        spikes (10-50ms). Scheduled GC during idle periods keeps heap healthy without
        affecting control timing.

    Args:
        threshold_kb: Run GC when free memory below this (default 60KB)

    Returns:
        None

    Raises:
        None

    Safety:
        GC runs max once per second. If heap critically low (<5KB), forces
        immediate collection to prevent OOM crash.

    Example:
        >>> gc_mgr = GarbageCollector(threshold_kb=60)
        >>> gc_mgr.process()  # Runs GC if needed
    """

    def __init__(self, threshold_kb: int = 60) -> None:
        self._threshold_bytes = threshold_kb * 1024
        self._last_gc_time = time.ticks_ms()
        self._min_interval_ms = 1000  # Max once per second
        self._critical_threshold_bytes = 5 * 1024  # 5KB critical

    def process(self) -> None:
        free_mem = gc.mem_free()
        now = time.ticks_ms()
        if free_mem < self._critical_threshold_bytes:
            try:
                gc.collect()
                self._last_gc_time = now
            except Exception:
                pass
            return
        if free_mem < self._threshold_bytes:
            if time.ticks_diff(now, self._last_gc_time) >= self._min_interval_ms:
                try:
                    gc.collect()
                    self._last_gc_time = now
                except Exception:
                    pass

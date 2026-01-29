"""
Non-blocking queue for file write operations.
"""
import time
from typing import List

class FileWriteQueue:
    """
    Non-blocking queue for file write operations.

    Why:
        JSON file writes (config.json, error_log.json) block for 10-50ms.
        Queuing writes allows main loop to continue without waiting for flash I/O.

    Args:
        max_size: Maximum pending writes (default 5)

    Returns:
        None

    Raises:
        None

    Safety:
        Queue size limited to 5 writes. Critical writes (emergency logs) take
        priority over routine writes (CV updates). Write failures logged but don't crash.

    Example:
        >>> queue = FileWriteQueue()
        >>> queue.enqueue_write("config.json", '{"CV1": 3}', priority=False)
        >>> queue.process()  # Writes one file if ready
    """

    def __init__(self, max_size: int = 5) -> None:
        self._queue: List[tuple] = []
        self._max_size = max_size
        self._last_write_time = time.ticks_ms()
        self._min_interval_ms = 100  # Minimum 100ms between writes

    def enqueue_write(self, filepath: str, content: str, priority: bool = False) -> None:
        if len(self._queue) >= self._max_size:
            if not priority:
                return  # Don't queue low-priority if full
            for i, (_, _, p) in enumerate(self._queue):
                if not p:
                    self._queue.pop(i)
                    break
        entry = (filepath, content, priority)
        if priority:
            self._queue.insert(0, entry)
        else:
            self._queue.append(entry)

    def process(self) -> None:
        now = time.ticks_ms()
        if time.ticks_diff(now, self._last_write_time) < self._min_interval_ms:
            return
        if len(self._queue) > 0:
            try:
                filepath, content, _ = self._queue.pop(0)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                self._last_write_time = now
            except Exception:
                pass  # Write failed, continue

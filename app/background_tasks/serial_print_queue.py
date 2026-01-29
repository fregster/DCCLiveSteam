"""
Non-blocking queue for USB serial output.
"""
from collections import deque
import time

class SerialPrintQueue:
    """
    Non-blocking queue for USB serial output.

    Why:
        print() can block for 2-5ms on USB serial. Queuing messages and writing
        in background keeps main loop timing predictable.

    Args:
        max_size: Maximum messages to buffer (default 10)

    Returns:
        None

    Raises:
        None

    Safety:
        Queue size limited to 10 messages. If full, oldest messages dropped
        (telemetry is not safety-critical). Non-blocking enqueue/dequeue operations.

    Example:
        >>> queue = SerialPrintQueue()
        >>> queue.enqueue("Speed: 45.3 cm/s")
        >>> queue.process()  # Prints one message if ready
    """

    def __init__(self, max_size: int = 10) -> None:
        self._queue: deque = deque((), max_size)
        self._last_print_time = time.ticks_ms()
        self._min_interval_ms = 50  # Minimum 50ms between prints

    def enqueue(self, message: str) -> None:
        try:
            self._queue.append(message)
        except Exception:
            pass  # Queue full, drop message (non-critical telemetry)

    def process(self) -> None:
        now = time.ticks_ms()
        if time.ticks_diff(now, self._last_print_time) < self._min_interval_ms:
            return
        if len(self._queue) > 0:
            try:
                message = self._queue.popleft()
                print(message)
                self._last_print_time = now
            except Exception:
                pass  # Print failed, continue

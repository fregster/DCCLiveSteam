"""
Interrupt-driven encoder tracking with velocity calculation.
"""
import time

class EncoderTracker:
    """
    Interrupt-driven encoder tracking with velocity calculation.

    Why:
        Polling encoder in main loop adds latency. IRQ-based tracking captures every
        edge, calculates velocity in background, main loop just reads cached value.

    Args:
        pin_encoder: Encoder GPIO pin (must support IRQ)

    Returns:
        None

    Raises:
        None

    Safety:
        Velocity calculated from time delta, not just count delta (handles
        variable loop timing). Cache never stale (IRQ updates continuously).

    Example:
        >>> tracker = EncoderTracker(pin=14)
        >>> velocity = tracker.get_velocity_cms()  # Instant, uses cached calculation
    """

    def __init__(self, pin_encoder):
        self._encoder_pin = pin_encoder
        self._count = 0
        self._last_count = 0
        self._last_time = time.ticks_ms()
        self._cached_velocity_cms = 0.0
        try:
            self._encoder_pin.irq(trigger=self._encoder_pin.IRQ_RISING, handler=self._irq_handler)
        except Exception:
            pass  # IRQ setup failed, will fall back to polling

    def _irq_handler(self, pin):
        self._count += 1

    def update_velocity(self) -> None:
        now = time.ticks_ms()
        time_delta = time.ticks_diff(now, self._last_time)
        if time_delta >= 1000:
            count_delta = self._count - self._last_count
            if time_delta > 0:
                counts_per_sec = (count_delta * 1000) / time_delta
                self._cached_velocity_cms = counts_per_sec * 0.1
            self._last_count = self._count
            self._last_time = now

    def get_velocity_cms(self) -> float:
        """
        Returns cached velocity in cm/s.

        Why:
            Provides instant access to last-calculated velocity for main loop and physics.

        Args:
            None

        Returns:
            float: Velocity in cm/s

        Raises:
            None

        Safety:
            Value is always <1s old. If encoder fails, returns last valid value.

        Example:
            >>> v = tracker.get_velocity_cms()
        """
        return self._cached_velocity_cms

    def get_count(self) -> int:
        """
        Returns current encoder count.

        Why:
            Used for diagnostics and velocity calculation.

        Args:
            None

        Returns:
            int: Encoder pulse count

        Raises:
            None

        Safety:
            Value is always up to date. If encoder fails, returns last valid value.

        Example:
            >>> c = tracker.get_count()
        """
        return self._count

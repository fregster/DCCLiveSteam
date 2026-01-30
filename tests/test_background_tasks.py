"""
Unit tests for background task managers.

Why: Background tasks handle non-critical operations (serial, file I/O, GC, sensor caching)
without blocking 50Hz control loop. Tests verify non-blocking behavior, queue limits,
rate limiting, and graceful degradation.
"""
import unittest
from unittest.mock import Mock, patch, mock_open
import time
from app.background_tasks import (SerialPrintQueue, FileWriteQueue, GarbageCollector,
                                  CachedSensorReader, EncoderTracker)


class TestSerialPrintQueue(unittest.TestCase):
    """Test serial print queue non-blocking operation."""

    def test_enqueue_message(self):
        """Verify messages can be queued without blocking."""
        queue = SerialPrintQueue(max_size=10)
        queue.enqueue("Test message")
        self.assertEqual(len(queue._queue), 1)

    def test_queue_size_limit(self):
        """Verify queue drops oldest when full."""
        queue = SerialPrintQueue(max_size=3)
        queue.enqueue("Message 1")
        queue.enqueue("Message 2")
        queue.enqueue("Message 3")
        queue.enqueue("Message 4")  # Should drop message 1
        self.assertEqual(len(queue._queue), 3)

    @patch('builtins.print')
    def test_process_prints_one_message(self, mock_print):
        """Verify process() prints one message per call."""
        queue = SerialPrintQueue(max_size=10)
        queue.enqueue("Message 1")
        queue.enqueue("Message 2")

        # Fast-forward time to bypass rate limit
        queue._last_print_time = time.ticks_ms() - 100

        queue.process()
        mock_print.assert_called_once_with("Message 1")
        self.assertEqual(len(queue._queue), 1)

    @patch('builtins.print')
    def test_rate_limiting(self, mock_print):
        """Verify minimum interval between prints enforced."""
        queue = SerialPrintQueue(max_size=10)
        queue.enqueue("Message 1")
        queue.enqueue("Message 2")

        # First print succeeds
        queue._last_print_time = time.ticks_ms() - 100
        queue.process()
        self.assertEqual(mock_print.call_count, 1)

        # Second print too soon (rate limited)
        queue.process()
        self.assertEqual(mock_print.call_count, 1)  # Still 1


class TestFileWriteQueue(unittest.TestCase):
    """Test file write queue non-blocking queuing."""

    def test_enqueue_write(self):
        """Verify file writes can be queued."""
        queue = FileWriteQueue(max_size=5)
        queue.enqueue_write("test.json", '{"key": "value"}', priority=False)
        self.assertEqual(len(queue._queue), 1)

    def test_priority_queue_ordering(self):
        """Verify priority writes added to front of queue."""
        queue = FileWriteQueue(max_size=5)
        queue.enqueue_write("low.json", "low", priority=False)
        queue.enqueue_write("high.json", "high", priority=True)

        # High priority should be first
        self.assertEqual(queue._queue[0][0], "high.json")

    def test_queue_full_drops_low_priority(self):
        """Verify queue drops low-priority when full."""
        queue = FileWriteQueue(max_size=2)
        queue.enqueue_write("file1.json", "1", priority=False)
        queue.enqueue_write("file2.json", "2", priority=False)
        queue.enqueue_write("file3.json", "3", priority=False)  # Dropped

        self.assertEqual(len(queue._queue), 2)

    @patch('builtins.open', new_callable=mock_open)
    def test_process_writes_one_file(self, mock_file):
        """Verify process() writes one file per call."""
        queue = FileWriteQueue(max_size=5)
        queue.enqueue_write("test.json", '{"test": true}', priority=False)

        # Fast-forward time to bypass rate limit
        queue._last_write_time = time.ticks_ms() - 200

        queue.process()
        mock_file.assert_called_once_with("test.json", "w", encoding="utf-8")
        self.assertEqual(len(queue._queue), 0)

    @patch('builtins.open', new_callable=mock_open)
    def test_rate_limiting(self, mock_file):
        """Verify minimum interval between writes enforced."""
        queue = FileWriteQueue(max_size=5)
        queue.enqueue_write("file1.json", "1", priority=False)
        queue.enqueue_write("file2.json", "2", priority=False)

        # First write succeeds
        queue._last_write_time = time.ticks_ms() - 200
        queue.process()
        self.assertEqual(mock_file.call_count, 1)

        # Second write too soon (rate limited)
        queue.process()
        self.assertEqual(mock_file.call_count, 1)  # Still 1


class TestGarbageCollector(unittest.TestCase):
    """Test scheduled garbage collection."""

    @patch('gc.mem_free', return_value=50 * 1024)  # 50KB free
    @patch('gc.collect')
    def test_gc_runs_when_below_threshold(self, mock_collect, mock_mem_free):
        """Verify GC runs when memory below threshold."""
        gc_mgr = GarbageCollector(threshold_kb=60)

        # Fast-forward time to bypass rate limit
        gc_mgr._last_gc_time = time.ticks_ms() - 2000

        gc_mgr.process()
        mock_collect.assert_called_once()

    @patch('gc.mem_free', return_value=70 * 1024)  # 70KB free
    @patch('gc.collect')
    def test_gc_skips_when_above_threshold(self, mock_collect, mock_mem_free):
        """Verify GC skipped when memory sufficient."""
        gc_mgr = GarbageCollector(threshold_kb=60)
        gc_mgr.process()
        mock_collect.assert_not_called()

    @patch('gc.mem_free', return_value=3 * 1024)  # 3KB free (critical!)
    @patch('gc.collect')
    def test_critical_memory_forces_immediate_gc(self, mock_collect, mock_mem_free):
        """Verify critical low memory forces GC regardless of timing."""
        gc_mgr = GarbageCollector(threshold_kb=60)

        # Just ran GC (should normally rate-limit)
        gc_mgr._last_gc_time = time.ticks_ms()

        gc_mgr.process()
        mock_collect.assert_called_once()  # Forces GC anyway

    @patch('gc.mem_free', return_value=50 * 1024)
    @patch('gc.collect')
    def test_rate_limiting(self, mock_collect, mock_mem_free):
        """Verify minimum interval between GC runs."""
        gc_mgr = GarbageCollector(threshold_kb=60)

        # First GC succeeds
        gc_mgr._last_gc_time = time.ticks_ms() - 2000
        gc_mgr.process()
        self.assertEqual(mock_collect.call_count, 1)

        # Second GC too soon (rate limited)
        gc_mgr.process()
        self.assertEqual(mock_collect.call_count, 1)  # Still 1


class TestCachedSensorReader(unittest.TestCase):
    """Test cached sensor reading."""

    def test_cached_reads_non_blocking(self):
        """Verify cached reads return immediately."""
        mock_sensors = Mock()
        reader = CachedSensorReader(mock_sensors)

        # Get temps (should be instant, no sensor call)
        temps = reader.get_temps()
        mock_sensors.read_temps.assert_not_called()
        self.assertEqual(temps, (25.0, 25.0, 25.0))  # Default

    def test_cache_refresh_when_stale(self):
        """Verify cache refreshed when old."""
        mock_sensors = Mock()
        mock_sensors.read_temps.return_value = (98.0, 245.0, 45.0)
        mock_sensors.read_pressure.return_value = 75.0
        mock_sensors.read_track_voltage.return_value = 12.5

        reader = CachedSensorReader(mock_sensors)

        # Force stale cache
        reader._last_update_time = time.ticks_ms() - 200

        reader.update_cache()

        # Verify sensors read and cache updated
        mock_sensors.read_temps.assert_called_once()
        self.assertEqual(reader.get_temps(), (98.0, 245.0, 45.0))
        self.assertEqual(reader.get_pressure(), 75.0)

    def test_cache_not_refreshed_when_fresh(self):
        """Verify cache not refreshed if recent."""
        mock_sensors = Mock()
        reader = CachedSensorReader(mock_sensors)

        # Cache is fresh
        reader._last_update_time = time.ticks_ms()

        reader.update_cache()

        # Verify sensors not read
        mock_sensors.read_temps.assert_not_called()

    def test_failed_read_keeps_old_values(self):
        """Verify sensor read failure keeps last-valid values."""
        mock_sensors = Mock()
        mock_sensors.read_temps.side_effect = Exception("Sensor failed")

        reader = CachedSensorReader(mock_sensors)
        old_temps = reader.get_temps()

        # Force cache refresh (will fail)
        reader._last_update_time = time.ticks_ms() - 200
        reader.update_cache()

        # Verify old values retained
        self.assertEqual(reader.get_temps(), old_temps)


class TestEncoderTracker(unittest.TestCase):
    """Test IRQ-based encoder tracking."""

    def test_velocity_initially_zero(self):
        """Verify velocity starts at zero."""
        mock_pin = Mock()
        tracker = EncoderTracker(mock_pin)
        self.assertEqual(tracker.get_velocity_cms(), 0.0)

    def test_irq_increments_count(self):
        """Verify IRQ handler increments count."""
        mock_pin = Mock()
        tracker = EncoderTracker(mock_pin)

        # Simulate IRQ firing
        tracker._irq_handler(mock_pin)
        tracker._irq_handler(mock_pin)
        tracker._irq_handler(mock_pin)

        self.assertEqual(tracker.get_count(), 3)

    def test_velocity_calculation(self):
        """Verify velocity calculated from count delta."""
        mock_pin = Mock()
        tracker = EncoderTracker(mock_pin)

        # Simulate encoder pulses
        tracker._count = 100

        # Force time delta (1 second elapsed)
        tracker._last_time = time.ticks_ms() - 1000

        tracker.update_velocity()

        # 100 counts/sec × 0.1 cm/count = 10 cm/s
        self.assertAlmostEqual(tracker.get_velocity_cms(), 10.0, places=1)

    def test_velocity_update_rate_limited(self):
        """Verify velocity only updated after 1 second."""
        mock_pin = Mock()
        tracker = EncoderTracker(mock_pin)

        old_velocity = tracker.get_velocity_cms()

        # Count changed but time too soon
        tracker._count = 50
        tracker._last_time = time.ticks_ms() - 500  # Only 500ms

        tracker.update_velocity()

        # Velocity not updated yet
        self.assertEqual(tracker.get_velocity_cms(), old_velocity)


if __name__ == '__main__':
    unittest.main()

"""
Unit tests for StatusReporter (app/status_reporter.py)
"""
from app.status_reporter import StatusReporter
from unittest.mock import MagicMock

def test_process_enqueues_message():
    queue = MagicMock()
    reporter = StatusReporter(queue, interval=2)
    reporter.process(10.0, 1.0, (100.0, 200.0, 50.0), 123, 4)
    queue.enqueue.assert_called()

def test_process_skips_if_not_interval():
    queue = MagicMock()
    reporter = StatusReporter(queue, interval=10)
    reporter.process(10.0, 1.0, (100.0, 200.0, 50.0), 123, 3)
    queue.enqueue.assert_not_called()
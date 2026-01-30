import time
from app.background_tasks.ble_telemetry_task import BLETelemetryTask
 
class DummyBLE:
    def __init__(self):
        self.sent = []
        self.processed = 0
    def send_telemetry(self, speed, psi, temps, servo_duty):
        self.sent.append((speed, psi, temps, servo_duty))
    def process_telemetry(self):
        self.processed += 1

def test_queue_and_process_telemetry(monkeypatch):
    ble = DummyBLE()
    task = BLETelemetryTask(ble, interval_ms=0)  # No wait for test
    task.queue_telemetry(1.0, 2.0, (3.0, 4.0, 5.0), 6)
    task.process()
    assert ble.sent == [(1.0, 2.0, (3.0, 4.0, 5.0), 6)]
    assert ble.processed == 1

def test_no_send_without_queue():
    ble = DummyBLE()
    task = BLETelemetryTask(ble, interval_ms=0)
    task.process()
    assert ble.sent == []
    assert ble.processed == 1

def test_interval_respected(monkeypatch):
    ble = DummyBLE()
    task = BLETelemetryTask(ble, interval_ms=100)
    # Patch time.ticks_ms to simulate time
    times = [0, 50, 150]
    monkeypatch.setattr(time, "ticks_ms", lambda: times.pop(0))
    task.queue_telemetry(1, 2, (3, 4, 5), 6)
    task.process()  # Should not send (only 0ms elapsed)
    assert ble.sent == []
    task.process()  # Should not send (only 50ms elapsed)
    assert ble.sent == []
    task.process()  # Should send (150ms elapsed)
    assert ble.sent == [(1, 2, (3, 4, 5), 6)]

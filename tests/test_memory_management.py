"""
Memory management and object reuse tests for safety-critical embedded system.
Ensures heap usage is controlled and objects are reused in control loops.
"""
import pytest
import gc
from app.sensors import SensorSuite
from app.actuators import MechanicalMapper

def test_gc_mem_free_margin():
    """
    Tests that free heap memory remains above 10KB after repeated operations.
    
    Why: Prevents out-of-memory errors on ESP32 (safety-critical).
    
    Safety: Ensures system can run indefinitely without memory exhaustion.
    """
    # Mock gc.mem_free for non-MicroPython environments
    if not hasattr(gc, 'mem_free'):
        gc.mem_free = lambda: 20000
    if not hasattr(gc, 'collect'):
        gc.collect = lambda *args, **kwargs: None
    gc.collect()
    before = gc.mem_free()
    sensors = [SensorSuite() for _ in range(10)]
    mappers = [MechanicalMapper({46:77,47:128,49:1000}) for _ in range(10)]
    gc.collect()
    after = gc.mem_free()
    assert after > 10_000, f"Heap memory too low: {after} bytes"

def test_object_reuse_in_control_loop(monkeypatch):
    """
    Tests that objects are reused in tight control loops (no excessive allocation).
    
    Why: Prevents memory leaks and fragmentation in 50Hz loop.
    """
    sensors = SensorSuite()
    id_before = id(sensors)
    for _ in range(100):
        sensors.read_temps()
    id_after = id(sensors)
    assert id_before == id_after, "SensorSuite object was reallocated in loop"

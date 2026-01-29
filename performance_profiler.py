"""
Performance Profiling Script for 50Hz Control Loop

This script instruments the main control loop to measure timing
of each subsystem and verify the 50Hz (20ms) requirement is met.

Why: Safety-critical system must maintain precise timing to prevent
servo jitter, missed DCC packets, or watchdog false positives.

Usage:
    1. Deploy to TinyPICO with profiling enabled
    2. Run for 60 seconds minimum
    3. Review statistics via BLE telemetry or serial console
    4. Verify worst-case timing < 20ms

Safety Note: Profiling adds ~0.5ms overhead per loop iteration.
Disable profiling in production builds.
"""

import time
import gc
from typing import Dict, List, Optional

class PerformanceProfiler:
    """
    Instruments control loop to measure subsystem timing.
    
    Why: Identify bottlenecks and verify real-time requirements.
    
    Attributes:
        enabled: Whether profiling is active
        results: Dictionary of timing statistics
    """
    
    def __init__(self, enabled: bool = True):
        """
        Initialise profiler with timing buckets.
        
        Args:
            enabled: Enable profiling on construction
        """
        self.enabled = enabled
        self.results: Dict[str, List[float]] = {
            "sensor_read": [],
            "physics_calc": [],
            "watchdog_check": [],
            "servo_update": [],
            "ble_telemetry": [],
            "total_loop": [],
            "gc_time": []
        }
        self._start_time: Optional[float] = None
        self._loop_start: Optional[float] = None
    
    def start_section(self, section: str) -> None:
        """
        Begin timing a subsystem section.
        
        Args:
            section: Name of subsystem being profiled
            
        Safety: Does nothing if profiling disabled.
        """
        if not self.enabled:
            return
        self._start_time = time.ticks_us()
    
    def end_section(self, section: str) -> None:
        """
        End timing a subsystem and record duration.
        
        Args:
            section: Name of subsystem being profiled
            
        Safety: Handles missing start_time gracefully.
        """
        if not self.enabled or self._start_time is None:
            return
        
        duration_us = time.ticks_diff(time.ticks_us(), self._start_time)
        duration_ms = duration_us / 1000.0
        
        if section in self.results:
            self.results[section].append(duration_ms)
        
        self._start_time = None
    
    def start_loop(self) -> None:
        """Begin timing a complete control loop iteration."""
        if not self.enabled:
            return
        self._loop_start = time.ticks_us()
    
    def end_loop(self) -> None:
        """End timing a control loop iteration."""
        if not self.enabled or self._loop_start is None:
            return
        
        duration_us = time.ticks_diff(time.ticks_us(), self._loop_start)
        duration_ms = duration_us / 1000.0
        self.results["total_loop"].append(duration_ms)
        self._loop_start = None
    
    def measure_gc(self) -> None:
        """
        Measure garbage collection execution time.
        
        Why: GC pauses can cause timing violations. Track duration
        to identify memory management issues.
        """
        if not self.enabled:
            return
        
        gc_start = time.ticks_us()
        gc.collect()
        gc_duration_us = time.ticks_diff(time.ticks_us(), gc_start)
        gc_duration_ms = gc_duration_us / 1000.0
        
        self.results["gc_time"].append(gc_duration_ms)
    
    def get_statistics(self) -> Dict[str, Dict[str, float]]:
        """
        Calculate timing statistics for all subsystems.
        
        Returns:
            Dictionary with min/max/avg/p95/p99 for each subsystem
            
        Example:
            >>> profiler.get_statistics()
            {
                "sensor_read": {
                    "min": 28.3,
                    "max": 32.1,
                    "avg": 30.2,
                    "p95": 31.5,
                    "p99": 31.9,
                    "samples": 3000
                },
                ...
            }
        """
        stats = {}
        
        for section, timings in self.results.items():
            if not timings:
                continue
            
            sorted_timings = sorted(timings)
            count = len(sorted_timings)
            
            # Calculate percentiles
            p95_idx = int(count * 0.95)
            p99_idx = int(count * 0.99)
            
            stats[section] = {
                "min": min(sorted_timings),
                "max": max(sorted_timings),
                "avg": sum(sorted_timings) / count,
                "p95": sorted_timings[p95_idx] if p95_idx < count else sorted_timings[-1],
                "p99": sorted_timings[p99_idx] if p99_idx < count else sorted_timings[-1],
                "samples": count
            }
        
        return stats
    
    def print_report(self) -> str:
        """
        Generate human-readable performance report.
        
        Returns:
            Multi-line string with formatted statistics
            
        Why: Easy diagnosis of timing violations or bottlenecks.
        """
        stats = self.get_statistics()
        
        lines = ["=" * 60]
        lines.append("PERFORMANCE PROFILING REPORT")
        lines.append("=" * 60)
        lines.append("")
        
        # Check for timing violations
        total_stats = stats.get("total_loop")
        if total_stats and total_stats["max"] > 20.0:
            lines.append("⚠️ WARNING: Timing violation detected!")
            lines.append(f"   Worst-case loop time: {total_stats['max']:.2f}ms (target: <20ms)")
            lines.append("")
        
        # Print each subsystem
        for section in ["sensor_read", "physics_calc", "watchdog_check",
                       "servo_update", "ble_telemetry", "total_loop", "gc_time"]:
            if section not in stats:
                continue
            
            data = stats[section]
            lines.append(f"{section.replace('_', ' ').title()}:")
            lines.append(f"  Min:     {data['min']:6.2f} ms")
            lines.append(f"  Avg:     {data['avg']:6.2f} ms")
            lines.append(f"  P95:     {data['p95']:6.2f} ms")
            lines.append(f"  P99:     {data['p99']:6.2f} ms")
            lines.append(f"  Max:     {data['max']:6.2f} ms")
            lines.append(f"  Samples: {data['samples']:6d}")
            lines.append("")
        
        # Memory statistics
        lines.append("Memory Status:")
        lines.append(f"  Free RAM: {gc.mem_free():,} bytes")
        lines.append(f"  Allocated: {gc.mem_alloc():,} bytes")
        lines.append("")
        
        # Calculate timing budget
        if total_stats:
            overhead = 20.0 - total_stats["avg"]
            lines.append(f"Timing Budget: {overhead:.2f}ms spare (avg case)")
            lines.append(f"50Hz Compliance: {'✅ PASS' if total_stats['max'] < 20.0 else '❌ FAIL'}")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def reset(self) -> None:
        """Clear all collected profiling data."""
        for key in self.results:
            self.results[key].clear()


# Example integration with main control loop
def profile_control_loop_example():
    """
    Example of how to integrate profiler into main.py.
    
    Why: Shows instrumentation points without modifying production code.
    """
    print("""
# In app/main.py, add profiling like this:

from performance_profiler import PerformanceProfiler

class Locomotive:
    def __init__(self, ...):
        # Enable profiling via CV or config flag
        self.profiler = PerformanceProfiler(enabled=False)  # Disabled by default
        
    def run(self):
        while True:
            self.profiler.start_loop()
            
            # Sensor reading
            self.profiler.start_section("sensor_read")
            temp_logic = self.sensors.read_temperature(...)
            temp_boiler = self.sensors.read_temperature(...)
            temp_superheater = self.sensors.read_temperature(...)
            pressure = self.sensors.read_pressure(...)
            self.profiler.end_section("sensor_read")
            
            # Physics calculation
            self.profiler.start_section("physics_calc")
            velocity = self.physics.get_velocity()
            self.profiler.end_section("physics_calc")
            
            # Watchdog
            self.profiler.start_section("watchdog_check")
            self.watchdog.check(...)
            self.profiler.end_section("watchdog_check")
            
            # Servo
            self.profiler.start_section("servo_update")
            self.regulator.set_position(...)
            self.profiler.end_section("servo_update")
            
            # BLE (every 1 second)
            if self.telemetry_counter >= 50:
                self.profiler.start_section("ble_telemetry")
                self.ble.send(...)
                self.profiler.end_section("ble_telemetry")
            
            self.profiler.end_loop()
            
            # Print report every 5 minutes (15,000 iterations)
            if self.loop_counter % 15000 == 0:
                print(self.profiler.print_report())
                self.profiler.reset()
            
            # GC measurement (every 100 loops)
            if self.loop_counter % 100 == 0:
                self.profiler.measure_gc()
            
            time.sleep_ms(20)
""")


if __name__ == "__main__":
    # Test profiler with simulated timings
    profiler = PerformanceProfiler(enabled=True)
    
    print("Simulating 100 control loop iterations...")
    for i in range(100):
        profiler.start_loop()
        
        profiler.start_section("sensor_read")
        time.sleep_ms(30)  # Simulate ADC
        profiler.end_section("sensor_read")
        
        profiler.start_section("physics_calc")
        time.sleep_ms(2)  # Simulate calculation
        profiler.end_section("physics_calc")
        
        profiler.start_section("watchdog_check")
        time.sleep_ms(1)
        profiler.end_section("watchdog_check")
        
        profiler.start_section("servo_update")
        time.sleep_ms(1)
        profiler.end_section("servo_update")
        
        if i % 50 == 0:  # Every second
            profiler.start_section("ble_telemetry")
            time.sleep_ms(5)
            profiler.end_section("ble_telemetry")
        
        profiler.end_loop()
        
        if i % 10 == 0:  # GC check
            profiler.measure_gc()
    
    print(profiler.print_report())
    profile_control_loop_example()

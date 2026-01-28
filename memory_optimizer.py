"""
Memory Optimization Analysis for ESP32 Live Steam Controller

This script identifies memory usage patterns and suggests optimizations
for the constrained MicroPython environment (~60KB free RAM).

Why: Heap fragmentation and excessive GC pauses can cause timing violations
in the 50Hz control loop.

Usage:
    1. Deploy to TinyPICO with memory tracking enabled
    2. Run locomotive for extended period (1+ hour)
    3. Analyse GC frequency and heap fragmentation
    4. Apply recommendations
"""

import gc
import sys
from typing import Dict, List, Tuple

class MemoryAnalyzer:
    """
    Tracks memory allocation patterns and GC behaviour.
    
    Why: Identify heap fragmentation and allocation hotspots that
    cause unpredictable GC pauses.
    
    Attributes:
        snapshots: List of (timestamp, free, allocated) tuples
        gc_events: List of GC execution times
    """
    
    def __init__(self):
        """Initialise memory tracking."""
        self.snapshots: List[Tuple[int, int, int]] = []
        self.gc_events: List[float] = []
        self._baseline_free: int = 0
        self._baseline_alloc: int = 0
    
    def capture_baseline(self) -> None:
        """
        Record initial memory state at boot.
        
        Why: Provides reference point for detecting memory leaks.
        """
        gc.collect()  # Clean slate
        self._baseline_free = gc.mem_free()
        self._baseline_alloc = gc.mem_alloc()
    
    def snapshot(self, timestamp: int) -> None:
        """
        Capture current memory state.
        
        Args:
            timestamp: Loop iteration counter or time.ticks_ms()
        """
        self.snapshots.append((
            timestamp,
            gc.mem_free(),
            gc.mem_alloc()
        ))
    
    def track_gc_time(self, duration_ms: float) -> None:
        """
        Record GC execution duration.
        
        Args:
            duration_ms: Time spent in gc.collect()
        """
        self.gc_events.append(duration_ms)
    
    def detect_memory_leak(self, threshold_bytes: int = 5000) -> bool:
        """
        Check if allocated memory is growing over time.
        
        Args:
            threshold_bytes: Max acceptable growth in allocated memory
            
        Returns:
            True if potential leak detected
            
        Why: Continuous allocation growth indicates objects not being freed.
        """
        if len(self.snapshots) < 10:
            return False  # Need enough samples
        
        # Compare first 10% of samples to last 10%
        early_avg = sum(s[2] for s in self.snapshots[:len(self.snapshots)//10]) \
                    / (len(self.snapshots)//10)
        late_avg = sum(s[2] for s in self.snapshots[-len(self.snapshots)//10:]) \
                   / (len(self.snapshots)//10)
        
        growth = late_avg - early_avg
        return growth > threshold_bytes
    
    def get_gc_statistics(self) -> Dict[str, float]:
        """
        Calculate GC timing statistics.
        
        Returns:
            Dictionary with min/max/avg/p95/p99 GC durations
        """
        if not self.gc_events:
            return {}
        
        sorted_times = sorted(self.gc_events)
        count = len(sorted_times)
        
        p95_idx = int(count * 0.95)
        p99_idx = int(count * 0.99)
        
        return {
            "min": min(sorted_times),
            "max": max(sorted_times),
            "avg": sum(sorted_times) / count,
            "p95": sorted_times[p95_idx] if p95_idx < count else sorted_times[-1],
            "p99": sorted_times[p99_idx] if p99_idx < count else sorted_times[-1],
            "count": count
        }
    
    def print_report(self) -> str:
        """
        Generate memory analysis report with optimization recommendations.
        
        Returns:
            Multi-line formatted report
        """
        lines = ["=" * 60]
        lines.append("MEMORY OPTIMIZATION REPORT")
        lines.append("=" * 60)
        lines.append("")
        
        # Current memory state
        gc.collect()
        current_free = gc.mem_free()
        current_alloc = gc.mem_alloc()
        
        lines.append("Current Memory State:")
        lines.append(f"  Free RAM:    {current_free:,} bytes")
        lines.append(f"  Allocated:   {current_alloc:,} bytes")
        lines.append(f"  Total:       {current_free + current_alloc:,} bytes")
        lines.append(f"  Utilization: {(current_alloc / (current_free + current_alloc)) * 100:.1f}%")
        lines.append("")
        
        # Baseline comparison
        if self._baseline_free > 0:
            free_delta = self._baseline_free - current_free
            alloc_delta = current_alloc - self._baseline_alloc
            
            lines.append("Memory Change Since Boot:")
            lines.append(f"  Free delta:  {free_delta:+,} bytes")
            lines.append(f"  Alloc delta: {alloc_delta:+,} bytes")
            lines.append("")
        
        # Memory leak detection
        if self.detect_memory_leak():
            lines.append("⚠️ WARNING: Potential memory leak detected!")
            lines.append("   Allocated memory growing over time.")
            lines.append("")
        
        # GC statistics
        gc_stats = self.get_gc_statistics()
        if gc_stats:
            lines.append("Garbage Collection Statistics:")
            lines.append(f"  Collections: {gc_stats['count']}")
            lines.append(f"  Min time:    {gc_stats['min']:.2f} ms")
            lines.append(f"  Avg time:    {gc_stats['avg']:.2f} ms")
            lines.append(f"  P95 time:    {gc_stats['p95']:.2f} ms")
            lines.append(f"  P99 time:    {gc_stats['p99']:.2f} ms")
            lines.append(f"  Max time:    {gc_stats['max']:.2f} ms")
            
            # Check for GC pauses exceeding timing budget
            if gc_stats['max'] > 5.0:
                lines.append("")
                lines.append("  ⚠️ Long GC pauses detected (>5ms)")
                lines.append("     Consider reducing allocation rate")
            lines.append("")
        
        # Optimization recommendations
        lines.append("OPTIMIZATION RECOMMENDATIONS:")
        lines.append("")
        
        if current_free < 30000:
            lines.append("🔴 CRITICAL: Low memory (<30KB free)")
            lines.append("   1. Reduce ADC oversampling (CV: not yet implemented)")
            lines.append("   2. Disable BLE telemetry if not needed")
            lines.append("   3. Reduce event buffer size (currently 20 entries)")
            lines.append("")
        elif current_free < 50000:
            lines.append("⚠️ WARNING: Memory pressure (<50KB free)")
            lines.append("   1. Monitor for allocation growth")
            lines.append("   2. Consider GC threshold adjustment")
            lines.append("")
        
        if gc_stats and gc_stats['avg'] > 3.0:
            lines.append("⚠️ GC overhead high (>3ms average)")
            lines.append("   Recommendations:")
            lines.append("   1. Pre-allocate buffers in __init__()")
            lines.append("   2. Reuse objects in control loop")
            lines.append("   3. Avoid string concatenation")
            lines.append("   4. Use bytearray for BLE data")
            lines.append("")
        
        # Specific code recommendations
        lines.append("Code-Specific Optimizations:")
        lines.append("")
        lines.append("1. Pre-allocate BLE telemetry buffer:")
        lines.append("   # Instead of: msg = f'V:{v} P:{p}...'")
        lines.append("   # Use: buffer = bytearray(64); format into buffer")
        lines.append("")
        lines.append("2. Reuse servo slew calculator state:")
        lines.append("   # Move _last_pwm to instance variable")
        lines.append("   # Avoid creating temp variables in loop")
        lines.append("")
        lines.append("3. Optimize ADC reading:")
        lines.append("   # Read all ADCs in one batch")
        lines.append("   # Cache conversions for stable readings")
        lines.append("")
        lines.append("4. DCC packet buffer:")
        lines.append("   # Preallocate 6-byte bytearray")
        lines.append("   # Reuse rather than create per packet")
        lines.append("")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)


# Integration example
def memory_tracking_example():
    """Show how to integrate memory tracking into main.py."""
    print("""
# In app/main.py, add memory tracking:

from memory_optimizer import MemoryAnalyzer

class Locomotive:
    def __init__(self, ...):
        self.mem_analyzer = MemoryAnalyzer()
        self.mem_analyzer.capture_baseline()
        
    def run(self):
        loop_counter = 0
        
        while True:
            # ... control loop ...
            
            # Track memory every 100 loops
            if loop_counter % 100 == 0:
                self.mem_analyzer.snapshot(loop_counter)
            
            # Measure GC time when triggered
            if gc.mem_free() < self.cv[46]:  # GC_THRESHOLD
                import time
                gc_start = time.ticks_us()
                gc.collect()
                gc_duration = time.ticks_diff(time.ticks_us(), gc_start) / 1000.0
                self.mem_analyzer.track_gc_time(gc_duration)
            
            # Print report every 30 minutes (90,000 loops)
            if loop_counter % 90000 == 0:
                print(self.mem_analyzer.print_report())
            
            loop_counter += 1
            time.sleep_ms(20)
""")


if __name__ == "__main__":
    # Test memory analyzer
    analyzer = MemoryAnalyzer()
    analyzer.capture_baseline()
    
    print("Simulating memory usage patterns...")
    
    # Simulate some allocation
    test_data = []
    for i in range(100):
        test_data.append({"iteration": i, "value": i * 1.5})
        analyzer.snapshot(i)
        
        if i % 10 == 0:
            gc.collect()
            analyzer.track_gc_time(2.3)  # Simulated GC time
    
    # Clear to simulate GC
    test_data = None
    gc.collect()
    
    print(analyzer.print_report())
    memory_tracking_example()

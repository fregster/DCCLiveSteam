"""
Safety watchdog system for live steam locomotive.
Monitors thermal limits and signal timeouts, triggers emergency shutdown.

Why: Live steam locomotives have multiple failure modes (dry boil, thermal runaway,
power loss). Multi-vector watchdog provides defense-in-depth against catastrophic
hardware damage and safety hazards.
"""
from typing import Dict, Any
import time

class Watchdog:
    """Monitors CV-defined thermal and signal thresholds.

    Why: Five independent safety vectors (logic temp, boiler temp, superheater temp,
    track voltage, DCC signal) prevent single-point failures. Each has CV-configurable
    threshold and timeout.

    Safety: Watchdog initialised with current time for power/DCC timers to prevent
    false triggers during first loop iteration after boot.

    Example:
        >>> watchdog = Watchdog()
        >>> watchdog.check(t_logic=45.0, t_boiler=95.0, t_super=200.0,
        ...                track_v=14000, dcc_active=True, cv=cv_table, loco=locomotive)
    """
    def __init__(self) -> None:
        """Initialise watchdog timers.

        Why: Power and DCC timers track time since last valid reading. Initialised to
        current time to prevent false timeout during startup (before first sensor read).

        Safety: Prevents spurious shutdown on first loop iteration where sensors may
        not have valid data yet. Shutdown guard prevents multiple die() calls during
        multi-fault scenarios.

        Example:
            >>> watchdog = Watchdog()
            >>> watchdog.pwr_t > 0
            True
        """
        self.pwr_t = time.ticks_ms()
        self.dcc_t = time.ticks_ms()
        self._shutdown_in_progress = False

    def check(self, t_logic: float, t_boiler: float, t_super: float,
              track_v: int, dcc_active: bool, cv: Dict[int, Any], loco: Any) -> None:
        """
        Checks all safety parameters and triggers shutdown if thresholds exceeded.

        Why: Called every 50Hz loop iteration (20ms) to detect thermal runaway or signal
        loss within <100ms. Early detection prevents boiler damage (thermal inertia ~60s)
        or uncontrolled operation after power loss.

        Args:
            t_logic: Logic bay temperature in Celsius (TinyPICO ambient sensor)
            t_boiler: Boiler shell temperature in Celsius (NTC thermistor)
            t_super: Superheater tube temperature in Celsius (NTC thermistor)
            track_v: Track voltage in millivolts (rectified DCC, 5x voltage divider)
            dcc_active: True if valid DCC packet decoded within last 500ms
            cv: CV configuration table with threshold keys:
                - 41: Logic temp limit (default 75°C)
                - 42: Boiler temp limit (default 110°C)
                - 43: Superheater temp limit (default 250°C)
                - 44: DCC timeout in 100ms units (default 5 = 500ms)
                - 45: Power timeout in 100ms units (default 10 = 1000ms)
            loco: Locomotive instance reference (for calling die() method)

        Safety: Thermal limits provide graduated protection (logic < boiler < superheater).
        Track voltage threshold (1500mV) detects <50% power drop. DCC timeout (500ms)
        allows for 16 missed packets (30ms NMRA refresh rate). Power timeout (1000ms)
        prevents false triggers from momentary track dirt.

        Calls loco.die() with cause string:
            - "LOGIC_HOT": TinyPICO overheating (firmware crash risk)
            - "DRY_BOIL": Boiler overtemp (water level low, heating element damage)
            - "SUPER_HOT": Superheater overtemp (steam pipe failure risk)
            - "PWR_LOSS": Track voltage lost (locomotive may coast to collision)
            - "DCC_LOST": DCC signal timeout (control loss)

        Example:
            >>> watchdog.check(45.0, 95.0, 200.0, 14000, True, cv_table, locomotive)
            >>> # Normal operation, no shutdown
            >>> watchdog.check(80.0, 95.0, 200.0, 14000, True, cv_table, locomotive)
            >>> # Triggers locomotive.die("LOGIC_HOT")
        """
        # Guard against multiple emergency shutdowns in multi-fault scenarios
        if self._shutdown_in_progress:
            return

        now = time.ticks_ms()

        # Thermal limits
        if t_logic > cv[41]:
            self._shutdown_in_progress = True
            loco.die("LOGIC_HOT")
            return
        if t_boiler > cv[42]:
            self._shutdown_in_progress = True
            loco.die("DRY_BOIL")
            return
        if t_super > cv[43]:
            self._shutdown_in_progress = True
            loco.die("SUPER_HOT")
            return

        # Power & DCC Signal Timers
        if track_v < 1500:
            if time.ticks_diff(now, self.pwr_t) > (cv[45] * 100):
                self._shutdown_in_progress = True
                loco.die("PWR_LOSS")
                return
        else:
            self.pwr_t = now

        if not dcc_active:
            if time.ticks_diff(now, self.dcc_t) > (cv[44] * 100):
                self._shutdown_in_progress = True
                loco.die("DCC_LOST")
                return
        else:
            self.dcc_t = now

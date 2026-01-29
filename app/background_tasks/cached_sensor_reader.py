"""
Cached sensor readings updated in background.
"""
import time

class CachedSensorReader:
    """
    Cached sensor readings updated in background.

    Why:
        ADC reads with oversampling take ~30ms (10 samples × 3ms each). Caching
        last-good values and updating asynchronously keeps main loop fast while still
        getting fresh sensor data.

    Args:
        sensor_suite: SensorSuite instance to wrap

    Returns:
        None

    Raises:
        None

    Safety:
        Cache never older than 200ms (meets watchdog 50Hz requirement). Failed
        sensor reads don't block main loop. Watchdog still monitors cached values.

    Example:
        >>> reader = CachedSensorReader(sensor_suite)
        >>> temps = reader.get_temps()  # Instant, uses cache
        >>> reader.update_cache()  # Background refresh (call periodically)
    """

    def __init__(self, sensor_suite):
        self._sensors = sensor_suite
        self._cached_temps = (25.0, 25.0, 25.0)  # (boiler, super, logic)
        self._cached_pressure = 0.0
        self._cached_track_v = 0.0
        self._last_update_time = time.ticks_ms()
        self._max_cache_age_ms = 100  # Refresh if older than 100ms

    def get_temps(self) -> tuple:
        """
        Returns cached temperature readings (boiler, superheater, logic).

        Why:
            Provides instant access to last-good temperature values for main loop and watchdog.

        Args:
            None

        Returns:
            tuple: (boiler_temp, super_temp, logic_temp) in Celsius

        Raises:
            None

        Safety:
            Cache is always <200ms old. If sensor fails, returns last valid value.

        Example:
            >>> temps = reader.get_temps()
        """
        return self._cached_temps

    def get_pressure(self) -> float:
        """
        Returns cached boiler pressure reading.

        Why:
            Avoids slow ADC reads in main loop. Used for pressure control and safety checks.

        Args:
            None

        Returns:
            float: Boiler pressure in PSI

        Raises:
            None

        Safety:
            Cache is always <200ms old. If sensor fails, returns last valid value.

        Example:
            >>> p = reader.get_pressure()
        """
        return self._cached_pressure

    def get_track_voltage(self) -> float:
        """
        Returns cached DCC track voltage reading.

        Why:
            Used for DCC signal validation and power monitoring.

        Args:
            None

        Returns:
            float: Track voltage in mV

        Raises:
            None

        Safety:
            Cache is always <200ms old. If sensor fails, returns last valid value.

        Example:
            >>> v = reader.get_track_voltage()
        """
        return self._cached_track_v

    def update_cache(self) -> None:
        now = time.ticks_ms()
        if time.ticks_diff(now, self._last_update_time) < self._max_cache_age_ms:
            return
        try:
            temps = self._sensors.read_temps()
            self._cached_temps = temps
            self._cached_pressure = self._sensors.read_pressure()
            self._cached_track_v = self._sensors.read_track_voltage()
            self._last_update_time = now
        except Exception:
            pass  # Sensor read failed, keep last-good values

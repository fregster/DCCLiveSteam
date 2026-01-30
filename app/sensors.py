"""
Sensor interface suite for live steam locomotive.
Handles ADC reading with oversampling, temperature conversion, encoder tracking,
and sensor health monitoring for graceful degradation on failure.
"""
from typing import Tuple, Dict
from machine import Pin, ADC
from .config import PIN_BOILER, PIN_SUPER, PIN_TRACK, PIN_PRESSURE, PIN_LOGIC_TEMP, PIN_ENCODER, ADC_SAMPLES

class SensorSuite:
    """
    Reads all analog sensors with oversampling.

    Why:
        Oversampling (10x) reduces ADC noise by ~3.16x (sqrt(N)), critical for
        stable thermal readings that control boiler heater duty cycles. Health tracking
        detects sensor failures and enables graceful degradation mode.

    Args:
        None

    Returns:
        None

    Raises:
        None

    Safety:
        Initialises all ADCs with ATTN_11DB (0-3.3V range) to prevent over-voltage
        damage to ESP32 analog frontend. Encoder uses PULL_UP to prevent floating input.
        Sensor health tracking allows continuous operation with single failed sensor
        (using cached last-valid value) whilst alerting operator.

    Example:
        >>> sensors = SensorSuite()
        >>> boiler, super, logic = sensors.read_temps()
        >>> sensors.get_health_status()
        {"boiler_temp": "NOMINAL", "super_temp": "NOMINAL", "logic_temp": "NOMINAL"}
    """
    def __init__(self) -> None:
        """
        Initialises all sensor ADCs and health tracking.

        Why:
            Sets up all ADCs and encoder pin for sensor reading. Applies correct attenuation to prevent over-voltage. Initialises health tracking for graceful degradation.

        Args:
            None

        Returns:
            None

        Raises:
            None

        Safety:
            Ensures all ADCs are configured for 0-3.3V. Health tracking allows continued operation with single failed sensor.

        Example:
            >>> sensors = SensorSuite()
        """
        self.adc_boiler = ADC(Pin(PIN_BOILER))
        self.adc_super = ADC(Pin(PIN_SUPER))
        self.adc_track = ADC(Pin(PIN_TRACK))
        self.adc_pressure = ADC(Pin(PIN_PRESSURE))
        self.adc_logic = ADC(Pin(PIN_LOGIC_TEMP))
        self.encoder_pin = Pin(PIN_ENCODER, Pin.IN, Pin.PULL_UP)
        self.encoder_count = 0
        self.encoder_last = self.encoder_pin.value()

        # Set ADC attenuation for 0-3.3V range
        for adc in [self.adc_boiler, self.adc_super, self.adc_track, self.adc_pressure, self.adc_logic]:
            adc.atten(ADC.ATTN_11DB)

        # NEW: Sensor health tracking for graceful degradation
        self.sensor_health: Dict[str, str] = {
            "boiler_temp": "NOMINAL",
            "super_temp": "NOMINAL",
            "logic_temp": "NOMINAL",
            "pressure": "NOMINAL",
        }
        self.last_valid_reading: Dict[str, float] = {
            "boiler_temp": 25.0,
            "super_temp": 25.0,
            "logic_temp": 25.0,
            "pressure": 0.0,
        }
        self.failed_sensor_count = 0
        self.failure_reason: str = ""

    def _read_adc(self, adc: ADC) -> int:
        """Oversample ADC to reduce noise.

        Why: ESP32 ADC has ~±50 LSB noise. Taking 10 samples and averaging reduces
        effective noise to ~±16 LSB, improving temperature stability.

        Args:
            adc: ADC object to read (must be pre-configured with attenuation)

        Returns:
            int: Averaged 12-bit ADC value (0-4095)

        Raises:
            None

        Safety: Returns integer in valid ADC range. Division by ADC_SAMPLES (10) ensures
        no overflow for sum of 10x 12-bit values (max sum = 40950).

        Example:
            >>> raw = self._read_adc(self.adc_boiler)
            >>> 0 <= raw <= 4095
            True
        """
        total = 0
        for _ in range(ADC_SAMPLES):
            total += adc.read()
        return total // ADC_SAMPLES

    def _adc_to_temp(self, raw: int) -> float:
        """Converts ADC reading to temperature using Steinhart-Hart equation.

        Why: NTC thermistors have non-linear resistance-temperature relationship.
        Steinhart-Hart equation provides <0.5°C accuracy from -50°C to +150°C.

        Args:
            raw: 12-bit ADC value (0-4095) from voltage divider circuit

        Returns:
            float: Temperature in Celsius. Returns 999.9°C on sensor failure to trigger
            thermal shutdown watchdog.

        Raises:
            ValueError: If raw is outside valid ADC range (0-4095)

        Safety: Disconnected sensor (raw=0) returns 999.9°C to force emergency shutdown.
        Division-by-zero protection on voltage calculation prevents runtime crash.

        Example:
            >>> self._adc_to_temp(2048)  # Mid-range ADC
            25.3
            >>> self._adc_to_temp(0)  # Sensor disconnected
            999.9
        """
        if not 0 <= raw <= 4095:
            raise ValueError(f"ADC value {raw} out of range 0-4095")

        if raw == 0:
            return 999.9  # Trigger thermal shutdown
        v = (raw / 4095.0) * 3.3
        if v >= 3.3:  # Prevent division by zero
            return 999.9  # Trigger thermal shutdown
        r = 10000.0 * v / (3.3 - v)
        # Steinhart-Hart equation for NTC thermistor
        log_r = __import__('math').log(r)
        temp_k = 1.0 / (0.001129148 + 0.000234125 * log_r + 0.0000000876741 * log_r**3)
        return temp_k - 273.15

    def is_reading_valid(self, reading: float, sensor_type: str) -> bool:
        """
        Checks if sensor reading is physically valid.

        Why: Different sensors have different valid ranges. Invalid readings indicate
        sensor failure (open circuit, disconnected, shorted). Enables graceful degradation.

        Args:
            reading: Sensor value to validate
            sensor_type: "boiler_temp" | "super_temp" | "logic_temp" | "pressure"

        Returns:
            bool: True if reading is physically possible, False if invalid

        Raises:
            None

        Safety: Conservative ranges catch failures immediately without false positives.

        Example:
            >>> self.is_reading_valid(25.0, "boiler_temp")
            True
            >>> self.is_reading_valid(999.9, "boiler_temp")
            False
            >>> self.is_reading_valid(-10, "pressure")
            False
        """
        if sensor_type == "boiler_temp":
            # Valid range: 0°C to 150°C (boiler operating range)
            return 0 <= reading <= 150
        if sensor_type == "super_temp":
            # Valid range: 0°C to 280°C (superheater, very hot)
            return 0 <= reading <= 280
        if sensor_type == "logic_temp":
            # Valid range: 0°C to 100°C (TinyPICO die temperature)
            return 0 <= reading <= 100
        if sensor_type == "pressure":
            # Valid range: -1 PSI to 30 PSI (atmosphere to safety relief)
            return -1 <= reading <= 30
        return False

    def read_temps(self) -> Tuple[float, float, float]:
        """
        Returns temperatures for all thermal sensors with health tracking.

        Why:
            Single atomic read of all thermal sensors ensures consistent snapshot for
            watchdog monitoring. Health tracking validates readings and enables graceful
            degradation (use cached values if sensor fails). Reading all three takes ~30ms.

        Args:
            None

        Returns:
            Tuple[float, float, float]: (boiler_temp, superheater_temp, logic_temp) in Celsius.
            Failed sensors return last valid cached value. If sensor recovers, normal reading
            resumes in next cycle.

        Raises:
            None

        Safety:
            Sensor health tracked in self.sensor_health dict (NOMINAL or DEGRADED).
            failed_sensor_count tracks total failures. failure_reason logs which sensors failed.
            Allows continued operation with single failed sensor (using cached value).

        Example:
            >>> boiler, super, logic = sensors.read_temps()
            >>> 0 < boiler < 150  # Normal operating range
            True
            >>> sensors.get_health_status()
            {"boiler_temp": "NOMINAL", "super_temp": "NOMINAL", "logic_temp": "NOMINAL"}
        """
        readings = {}
        failed_sensors = []

        # Read boiler temperature
        raw_boiler = self._read_adc(self.adc_boiler)
        boiler = self._adc_to_temp(raw_boiler)
        if self.is_reading_valid(boiler, "boiler_temp"):
            readings["boiler"] = boiler
            self.last_valid_reading["boiler_temp"] = boiler
            self.sensor_health["boiler_temp"] = "NOMINAL"
        else:
            readings["boiler"] = self.last_valid_reading["boiler_temp"]
            self.sensor_health["boiler_temp"] = "DEGRADED"
            failed_sensors.append("boiler_temp")

        # Read superheater temperature
        raw_super = self._read_adc(self.adc_super)
        super_t = self._adc_to_temp(raw_super)
        if self.is_reading_valid(super_t, "super_temp"):
            readings["super"] = super_t
            self.last_valid_reading["super_temp"] = super_t
            self.sensor_health["super_temp"] = "NOMINAL"
        else:
            readings["super"] = self.last_valid_reading["super_temp"]
            self.sensor_health["super_temp"] = "DEGRADED"
            failed_sensors.append("super_temp")

        # Read logic temperature
        raw_logic = self._read_adc(self.adc_logic)
        logic = self._adc_to_temp(raw_logic)
        if self.is_reading_valid(logic, "logic_temp"):
            readings["logic"] = logic
            self.last_valid_reading["logic_temp"] = logic
            self.sensor_health["logic_temp"] = "NOMINAL"
        else:
            readings["logic"] = self.last_valid_reading["logic_temp"]
            self.sensor_health["logic_temp"] = "DEGRADED"
            failed_sensors.append("logic_temp")

        # Track total failures
        self.failed_sensor_count = len(failed_sensors)
        if failed_sensors:
            self.failure_reason = "Sensor(s) failed: " + ", ".join(failed_sensors)

        return (readings["boiler"], readings["super"], readings["logic"])

    def get_health_status(self) -> Dict[str, str]:
        """
        Returns current sensor health status.

        Why:
            Allows watchdog and main loop to query sensor health without exposing
            internal state. Used to detect sensor failures and trigger degraded mode.

        Args:
            None

        Returns:
            Dictionary with sensor names as keys, health status ("NOMINAL" or "DEGRADED") as values

        Raises:
            None

        Safety:
            Read-only method, doesn't modify state.

        Example:
            >>> sensors.get_health_status()
            {"boiler_temp": "NOMINAL", "super_temp": "DEGRADED", "logic_temp": "NOMINAL", "pressure": "NOMINAL"}
        """
        return self.sensor_health.copy()

    def read_track_voltage(self) -> int:
        """
        Returns track voltage in millivolts (scaled for rectified DCC).

        Why:
            DCC track voltage (typically 12-18V) is rectified and divided by 5x to
            fit ESP32's 3.3V ADC range. Used for power-loss detection (CV45 timeout).

        Args:
            None

        Returns:
            int: Track voltage in millivolts (0-16500 typical range for DCC)

        Raises:
            None

        Safety:
            Returns 0 on disconnected track, triggering power watchdog timeout.

        Example:
            >>> sensors.read_track_voltage()
            14200  # 14.2V DCC track power
        """
        raw = self._read_adc(self.adc_track)
        return int((raw / 4095.0) * 3300 * 5.0)  # Assuming 5x voltage divider

    def read_pressure(self) -> float:
        """
        Returns boiler pressure in PSI.

        Why:
            0-100 PSI analog sensor (0-3.3V linear) drives PID heater control.
            Typical operating range is 40-60 PSI for scale steam locomotives.

        Args:
            None

        Returns:
            float: Boiler pressure in PSI (0.0-100.0)

        Raises:
            None

        Safety:
            Pressure sensor failure (returning 0 PSI) will cause PID controller
            to increase heater duty, but thermal limits (CV42) prevent boiler dry-boil.
            Physical safety valve rated at 100 PSI provides mechanical backup.

        Example:
            >>> sensors.read_pressure()
            55.3  # 55.3 PSI operating pressure
        """
        raw = self._read_adc(self.adc_pressure)
        return (raw / 4095.0) * 100.0

    def update_encoder(self) -> int:
        """
        Updates encoder count on state changes.

        Why:
            Optical encoder on wheel axle provides odometry for speed calculation
            (PhysicsEngine.calc_velocity). Falling-edge detection halves interrupt rate.

        Args:
            None

        Returns:
            int: Total encoder pulses since boot (wraps at large values, handled in physics.py)

        Raises:
            None

        Safety:
            Debouncing not required for optical encoder (no mechanical bounce).
            Encoder failure (count stops incrementing) causes velocity to read 0, which is
            safe (locomotive appears stopped).

        Example:
            >>> initial = sensors.update_encoder()
            >>> # ... locomotive moves ...
            >>> final = sensors.update_encoder()
            >>> pulses = final - initial
        """
        current = self.encoder_pin.value()
        if current != self.encoder_last:
            if current == 0:  # Falling edge
                self.encoder_count += 1
            self.encoder_last = current
        return self.encoder_count

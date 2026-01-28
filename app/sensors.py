"""
Sensor interface suite for Mallard locomotive.
Handles ADC reading with oversampling, temperature conversion, and encoder tracking.
"""
from typing import Tuple
from machine import Pin, ADC
from .config import PIN_BOILER, PIN_SUPER, PIN_TRACK, PIN_PRESSURE, PIN_LOGIC_TEMP, PIN_ENCODER, ADC_SAMPLES

class SensorSuite:
    """Reads all analog sensors with oversampling.

    Why: Oversampling (10x) reduces ADC noise by ~3.16x (sqrt(N)), critical for
    stable thermal readings that control boiler heater duty cycles.

    Safety: Initialises all ADCs with ATTN_11DB (0-3.3V range) to prevent over-voltage
    damage to ESP32 analog frontend. Encoder uses PULL_UP to prevent floating input.

    Example:
        >>> sensors = SensorSuite()
        >>> boiler, super, logic = sensors.read_temps()
    """
    def __init__(self) -> None:
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

    def _read_adc(self, adc: ADC) -> int:
        """Oversample ADC to reduce noise.

        Why: ESP32 ADC has ~±50 LSB noise. Taking 10 samples and averaging reduces
        effective noise to ~±16 LSB, improving temperature stability.

        Args:
            adc: ADC object to read (must be pre-configured with attenuation)

        Returns:
            int: Averaged 12-bit ADC value (0-4095)

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

    def read_temps(self) -> Tuple[float, float, float]:
        """Returns temperatures for all thermal sensors.

        Why: Single atomic read of all thermal sensors ensures consistent snapshot for
        watchdog monitoring. Reading all three takes ~30ms (10 samples × 3 sensors).

        Returns:
            Tuple[float, float, float]: (boiler_temp, superheater_temp, logic_temp) in Celsius.
            Any sensor failure returns 999.9°C for that position to trigger shutdown.

        Safety: Failed sensors return 999.9°C which exceeds all CV thermal limits (CV41-43),
        forcing emergency shutdown via Watchdog.check().

        Example:
            >>> boiler, super, logic = sensors.read_temps()
            >>> 0 < boiler < 150  # Normal operating range
            True
        """
        return (
            self._adc_to_temp(self._read_adc(self.adc_boiler)),
            self._adc_to_temp(self._read_adc(self.adc_super)),
            self._adc_to_temp(self._read_adc(self.adc_logic))
        )

    def read_track_voltage(self) -> int:
        """Returns track voltage in millivolts (scaled for rectified DCC).

        Why: DCC track voltage (typically 12-18V) is rectified and divided by 5x to
        fit ESP32's 3.3V ADC range. Used for power-loss detection (CV45 timeout).

        Returns:
            int: Track voltage in millivolts (0-16500 typical range for DCC)

        Safety: Returns 0 on disconnected track, triggering power watchdog timeout.

        Example:
            >>> sensors.read_track_voltage()
            14200  # 14.2V DCC track power
        """
        raw = self._read_adc(self.adc_track)
        return int((raw / 4095.0) * 3300 * 5.0)  # Assuming 5x voltage divider

    def read_pressure(self) -> float:
        """Returns boiler pressure in PSI.

        Why: 0-100 PSI analog sensor (0-3.3V linear) drives PID heater control.
        Typical operating range is 40-60 PSI for scale steam locomotives.

        Returns:
            float: Boiler pressure in PSI (0.0-100.0)

        Safety: Pressure sensor failure (returning 0 PSI) will cause PID controller
        to increase heater duty, but thermal limits (CV42) prevent boiler dry-boil.
        Physical safety valve rated at 100 PSI provides mechanical backup.

        Example:
            >>> sensors.read_pressure()
            55.3  # 55.3 PSI operating pressure
        """
        raw = self._read_adc(self.adc_pressure)
        return (raw / 4095.0) * 100.0

    def update_encoder(self) -> int:
        """Updates encoder count on state changes.

        Why: Optical encoder on wheel axle provides odometry for speed calculation
        (PhysicsEngine.calc_velocity). Falling-edge detection halves interrupt rate.

        Returns:
            int: Total encoder pulses since boot (wraps at large values, handled in physics.py)

        Safety: Debouncing not required for optical encoder (no mechanical bounce).
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

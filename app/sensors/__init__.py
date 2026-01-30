
"""
Sensors package: pressure, speed, temperature, etc.
Unified SensorSuite interface.
"""
from machine import ADC, Pin
from .pressure_sensor import read_pressure
from .speed_sensor import SpeedSensor
from .temperature_sensor import read_temps
from .track_voltage_sensor import read_track_voltage
from .health import is_reading_valid
from ..config import PIN_BOILER, PIN_SUPER, PIN_TRACK, PIN_PRESSURE, PIN_LOGIC_TEMP, PIN_ENCODER, ADC_SAMPLES

class SensorSuite:
	"""
	Unified interface for all sensors (pressure, speed, temperature, track voltage).
	Handles ADC initialisation and delegates to sensor modules.

	Fallback/Degraded Mode:
		- If speed sensor is unavailable or fails, speed_sensor_available is set False for manager fallback.
		- If pressure sensor is unavailable or fails, pressure_sensor_available is set False for manager fallback.
		- Temperature sensors are always required for safety; if they fail, system must shut down.
	"""
	def __init__(self):
		self.adc_boiler = ADC(Pin(PIN_BOILER))
		self.adc_super = ADC(Pin(PIN_SUPER))
		self.adc_track = ADC(Pin(PIN_TRACK))
		self.adc_pressure = ADC(Pin(PIN_PRESSURE))
		self.adc_logic = ADC(Pin(PIN_LOGIC_TEMP))
		# Sensor health flags
		self.speed_sensor_available = True
		self.pressure_sensor_available = True
		# Speed sensor init with health check
		try:
			self.speed_sensor = SpeedSensor()
			# Try to update encoder to check health
			_ = self.speed_sensor.update_encoder()
		except Exception:
			self.speed_sensor_available = False
			self.speed_sensor = None
		# Expose legacy encoder attributes for test compatibility
		self.encoder_pin = self.speed_sensor.encoder_pin if self.speed_sensor else None
		self.encoder_count = self.speed_sensor.encoder_count if self.speed_sensor else 0
		self.encoder_last = self.speed_sensor.encoder_last if self.speed_sensor else 0
		# Pressure sensor health check (try reading once)
		try:
			_ = read_pressure(self.adc_pressure)
		except Exception:
			self.pressure_sensor_available = False
	def check_health(self):
		"""
		Checks health of all sensors and updates availability flags.
		Returns a dict of sensor health status.
		"""
		# Speed sensor
		self.speed_sensor_available = False
		try:
			if self.speed_sensor is not None:
				_ = self.speed_sensor.update_encoder()
				self.speed_sensor_available = True
		except Exception:
			self.speed_sensor_available = False
			self.speed_sensor = None
		# Pressure sensor
		try:
			_ = read_pressure(self.adc_pressure)
			self.pressure_sensor_available = True
		except Exception:
			self.pressure_sensor_available = False
		# Temperature sensors are checked in read_temps
		return {
			"speed_sensor": self.speed_sensor_available,
			"pressure_sensor": self.pressure_sensor_available,
		}

	@property
	def encoder_count(self):
		if self.speed_sensor is not None:
			return self.speed_sensor.encoder_count
		return 0

	@encoder_count.setter
	def encoder_count(self, value):
		if self.speed_sensor is not None:
			self.speed_sensor.encoder_count = value

	@property
	def encoder_last(self):
		if self.speed_sensor is not None:
			return self.speed_sensor.encoder_last
		return 0

	@encoder_last.setter
	def encoder_last(self, value):
		if self.speed_sensor is not None:
			self.speed_sensor.encoder_last = value
		# Set ADC attenuation for 0-3.3V range
		for adc in [self.adc_boiler, self.adc_super, self.adc_track, self.adc_pressure, self.adc_logic]:
			adc.atten(ADC.ATTN_11DB)

		# Graceful degradation state
		self._cached_temps = {
			"boiler_temp": 25.0,
			"super_temp": 25.0,
			"logic_temp": 25.0
		}
		self._health = {
			"boiler_temp": "NOMINAL",
			"super_temp": "NOMINAL",
			"logic_temp": "NOMINAL",
			"pressure": "NOMINAL"
		}
		self.failed_sensor_count = 0
		self.failure_reason = set()

	def read_temps(self):
		from .temperature_sensor import _read_adc, _adc_to_temp
		temps = {}
		health = {}
		failed = 0
		reasons = set()
		# Boiler
		raw_boiler = _read_adc(self.adc_boiler)
		temp_boiler = _adc_to_temp(raw_boiler)
		if temp_boiler == 999.9:
			temp_boiler = self._cached_temps["boiler_temp"]
			health["boiler_temp"] = "DEGRADED"
			failed += 1
			reasons.add("boiler_temp")
		else:
			self._cached_temps["boiler_temp"] = temp_boiler
			health["boiler_temp"] = "NOMINAL"
		# Superheater
		raw_super = _read_adc(self.adc_super)
		temp_super = _adc_to_temp(raw_super)
		if temp_super == 999.9:
			temp_super = self._cached_temps["super_temp"]
			health["super_temp"] = "DEGRADED"
			failed += 1
			reasons.add("super_temp")
		else:
			self._cached_temps["super_temp"] = temp_super
			health["super_temp"] = "NOMINAL"
		# Logic
		raw_logic = _read_adc(self.adc_logic)
		temp_logic = _adc_to_temp(raw_logic)
		if temp_logic == 999.9:
			temp_logic = self._cached_temps["logic_temp"]
			health["logic_temp"] = "DEGRADED"
			failed += 1
			reasons.add("logic_temp")
		else:
			self._cached_temps["logic_temp"] = temp_logic
			health["logic_temp"] = "NOMINAL"
		self._health = health
		self.failed_sensor_count = failed
		self.failure_reason = reasons
		return (temp_boiler, temp_super, temp_logic)

	# Legacy methods for test compatibility
	def _read_adc(self, adc):
		from .temperature_sensor import _read_adc
		return _read_adc(adc)

	def _adc_to_temp(self, raw):
		from .temperature_sensor import _adc_to_temp
		return _adc_to_temp(raw)

	def get_health_status(self):
		return self._health.copy()

	def read_pressure(self):
		return read_pressure(self.adc_pressure)

	def read_track_voltage(self):
		return read_track_voltage(self.adc_track)

	def update_encoder(self):
		count = self.speed_sensor.update_encoder()
		self.encoder_count = self.speed_sensor.encoder_count
		self.encoder_last = self.speed_sensor.encoder_last
		return count

	def is_reading_valid(self, reading, sensor_type):
		return is_reading_valid(reading, sensor_type)

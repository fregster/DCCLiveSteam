"""
Speed sensor (encoder) reading and conversion logic.
"""
from machine import Pin
from ..config import PIN_ENCODER

class SpeedSensor:
	def __init__(self):
		self.encoder_pin = Pin(PIN_ENCODER, Pin.IN, Pin.PULL_UP)
		self.encoder_count = 0
		self.encoder_last = self.encoder_pin.value()

	def update_encoder(self) -> int:
		current = self.encoder_pin.value()
		if current != self.encoder_last:
			if current == 0:
				self.encoder_count += 1
			self.encoder_last = current
		return self.encoder_count

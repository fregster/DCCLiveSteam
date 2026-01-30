"""
Speed sensor (encoder) reading and conversion logic.
"""
from app.hardware_interfaces import ISensor


class SpeedSensor(ISensor):
	def __init__(self, encoder_hw):
		"""
		Args:
			encoder_hw: Hardware abstraction implementing read() for encoder pin
		"""
		self.encoder_hw = encoder_hw
		self.encoder_count = 0
		self.encoder_last = self.encoder_hw.read()

	def update_encoder(self) -> int:
		current = self.encoder_hw.read()
		# Only increment on falling edge: last==1, current==0
		if self.encoder_last == 1 and current == 0:
			self.encoder_count += 1
		self.encoder_last = current
		return self.encoder_count

	def read(self) -> int:
		"""Implements ISensor interface."""
		return self.update_encoder()

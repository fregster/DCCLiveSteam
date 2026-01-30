"""
Pressure sensor reading and conversion logic.
"""
from machine import ADC
from ..config import ADC_SAMPLES

def _read_adc(adc: ADC) -> int:
	total = 0
	for _ in range(ADC_SAMPLES):
		total += adc.read()
	return total // ADC_SAMPLES

def read_pressure(adc_pressure) -> float:
	raw = _read_adc(adc_pressure)
	return (raw / 4095.0) * 100.0

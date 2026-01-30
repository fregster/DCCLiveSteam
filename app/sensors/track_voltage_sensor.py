"""
Track voltage sensor reading logic.
"""
from machine import ADC
from ..config import ADC_SAMPLES

def _read_adc(adc: ADC) -> int:
    total = 0
    for _ in range(ADC_SAMPLES):
        total += adc.read()
    return total // ADC_SAMPLES

def read_track_voltage(adc_track) -> int:
    raw = _read_adc(adc_track)
    return int((raw / 4095.0) * 3300 * 5.0)

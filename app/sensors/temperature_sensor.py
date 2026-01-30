"""
Temperature sensor ADC reading and conversion logic.
"""
from machine import ADC
from ..config import ADC_SAMPLES
import math

def _read_adc(adc: ADC) -> int:
    total = 0
    for _ in range(ADC_SAMPLES):
        total += adc.read()
    return total // ADC_SAMPLES

def _adc_to_temp(raw: int) -> float:
    if not 0 <= raw <= 4095:
        raise ValueError(f"ADC value {raw} out of range 0-4095")
    if raw == 0:
        return 999.9
    v = (raw / 4095.0) * 3.3
    if v >= 3.3:
        return 999.9
    r = 10000.0 * v / (3.3 - v)
    log_r = math.log(r)
    temp_k = 1.0 / (0.001129148 + 0.000234125 * log_r + 0.0000000876741 * log_r**3)
    return temp_k - 273.15

def read_temps(adc_boiler, adc_super, adc_logic):
    return (
        _adc_to_temp(_read_adc(adc_boiler)),
        _adc_to_temp(_read_adc(adc_super)),
        _adc_to_temp(_read_adc(adc_logic)),
    )

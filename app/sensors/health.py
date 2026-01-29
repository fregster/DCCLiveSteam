"""
Sensor health tracking logic.
"""
def is_reading_valid(reading: float, sensor_type: str) -> bool:
    if sensor_type == "boiler_temp":
        return 0 <= reading <= 150
    elif sensor_type == "super_temp":
        return 0 <= reading <= 280
    elif sensor_type == "logic_temp":
        return 0 <= reading <= 100
    elif sensor_type == "pressure":
        return -1 <= reading <= 30
    else:
        return False

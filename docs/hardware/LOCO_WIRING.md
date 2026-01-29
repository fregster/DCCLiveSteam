# Locomotive Board Wiring Diagram

```
+-------------------+         +-------------------+
|   Loco Board      |         |   Sensors/Actuators|
|-------------------|         |-------------------|
| Heater 1 PWM <----|---------+----[Heater Coil 1]---[1N4007]---+
| Heater 2 PWM <----|---------+----[Heater Coil 2]---[1N4007]---+
| Servo PWM  <------|---------+----[MG90S Servo]                |
| I2C SDA/SCL <-----|---------+----[MLX90614 #1, #2, Pressure]  |
| Sensor VCC <------|---------+----[Thermocouple Amp, Sensors]  |
| GND <-------------|---------+----[All Sensor/Actuator GND]    |
|                   |         |                                 |
| [TCRT5000]--------|---------+----> Speed/Odometry Input       |
+-------------------+         +-------------------+
```

- All connections come from the umbilical.
- Heaters are controlled by PWM from the Tender, with local flyback diodes.
- I2C bus shared by MLX90614 sensors and pressure sensor.
- Servo receives PWM directly from Tender.
- Odometry sensor connects to digital input.

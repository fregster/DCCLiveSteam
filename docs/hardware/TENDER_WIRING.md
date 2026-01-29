# Tender (Boiler) Board Wiring Diagram

```
+-------------------+         +-------------------+
|   TinyPICO ESP32  |         |   Power Section   |
|-------------------|         |-------------------|
| GPIO 14 <---------|---[6N137 Opto]---< DCC Track Signal
| GPIO 21 (SDA) ----|-------------------+--------> I2C Bus (to Loco)
| GPIO 22 (SCL) ----|-------------------+--------> I2C Bus (to Loco)
| GPIO 25 ----------|---[100Ω]---+      |        > Heater 1 PWM (to Loco)
|                   |            |      |
| GPIO 26 ----------|---[100Ω]---+      |        > Heater 2 PWM (to Loco)
|                   |            |      |
| GPIO 27 ----------|-------------------> Servo PWM (to Loco)
| GPIO 34 <---------|-------------------< Water Level Sensor
| 3.3V/5V ----------|-------------------> Sensor VCC (to Loco)
| GND --------------|-------------------> GND (to Loco)
+-------------------+         +-------------------+
         |                                   |
         +--------[MP1584EN Buck]------------+
         |                                   |
         +--------[Supercaps]----------------+
```

- All PWM and I2C lines go to the umbilical connector.
- MOSFETs for heater control are on the Tender board, with outputs routed to the Loco.
- Power input from DCC track via bridge rectifier.

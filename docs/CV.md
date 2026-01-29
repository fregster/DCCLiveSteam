CV,Parameter,Default,Unit,Description
1,Primary Address,3,ID,The short DCC address of the locomotive.
29,Configuration,6,Bit,Bit 1: 128-step mode; Bit 2: DC Enable.
30,Failsafe Mode,1,Bool,"1 = ""Distress Whistle"" on shutdown; 0 = Silent."
31,Servo Offset,0,PWM,Fine-tunes the physical neutral (closed) point.
32,Target Pressure,124.0,kPa,The desired operating steam pressure (default 124 kPa; 18.0 PSI reference).
35,Max Boiler Pressure,207.0,kPa,Maximum allowed boiler pressure (user limit, default 207 kPa; 30 PSI reference, Hornby safety valve). System will shut down if exceeded.
33,Stiction Breakout,35.0,%,Momentary regulator kick to start from a dead stop.
34,Slip Sensitivity,15.0,%,Threshold for wheel-slip detection vs. ground speed.
37,Wheel Radius,1325,0.01mm,"Radius of the driving wheels (e.g., 1325 = 13.25mm)."
38,Encoder Count,12,Segs,Number of light/dark segments on the optical disc.
39,Prototype Speed,203,km/h,Max speed of the real locomotive (e.g., 203 km/h for A4 class).
40,Scale Ratio,76,Ratio,"76 for OO (1:76), 87 for HO (1:87)."
41,Watchdog: Logic,75,°C,Shutdown if TinyPICO internal temp exceeds this.
42,Watchdog: Boiler,110,°C,Dry-Boil Guard: Shutdown if boiler exceeds this.
43,Watchdog: Super,250,°C,Gasket Guard: Shutdown if steam pipes exceed this.
44,Watchdog: DCC,20,0.1s,"Lost signal timeout (e.g., 20 = 2.0 seconds)."
45,Watchdog: Power,8,0.1s,"Power loss timeout (e.g., 8 = 0.8 seconds)."
46,Servo Neutral,77,Duty,PWM duty cycle for fully closed regulator (0°).
47,Servo Max,128,Duty,PWM duty cycle for fully open regulator (90°).
48,Whistle Offset,5,Deg,Degrees from neutral to trigger whistle blow-off.
49,Travel Time,1000,ms,Time to sweep from 0% to 100% regulator open.
84,Graceful Degradation,1,Bool,"1 = Smooth deceleration on sensor failure; 0 = Immediate shutdown."
87,Decel Rate,10.0,cm/s²,Speed of controlled deceleration during sensor failure graceful shutdown.

51,Power Budget,4.5,Amps,Maximum total system current draw (all loads). System will shed non-critical loads or reduce power to stay within this limit. Exceeding this triggers a safety shutdown.
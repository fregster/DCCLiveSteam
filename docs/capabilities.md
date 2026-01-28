Here is the comprehensive list of capabilities for the Mallard-ESP32 control system, formatted for your project documentation.

1. System Initialization & Provisioning
Auto-Provisioning: On boot, the system checks for necessary configuration files (config.json, error_log.json) and automatically creates them with factory defaults if they are missing or corrupted.

CV Table Architecture: A centralized dictionary for Configuration Variables (CVs) allows for real-time tuning of physical and logical parameters without flashing new code.

JSON Persistence: Automatically saves and loads CV settings from internal flash storage to maintain calibration across power cycles.

2. Advanced Motion & Physics
Prototype-to-Scale Mapping: Translates prototype speed (km/h) into model scale speed (cm/s) based on user-defined scale ratios (e.g., 1:76 for OO or 1:87 for HO).

High-Resolution Speed Interpretation: Full support for 128-step DCC speed commands for ultra-smooth throttle response.

Stiction Breakout Logic: Provides a momentary "kick" to the regulator to overcome mechanical friction (stiction) when starting from a standstill.

Encoder-Based Odometry: Calibrates speed based on a 12-segment optical wheel encoder and the precise radius of the driving wheels.

3. Precision Mechanical Regulation
Slew-Rate Limiting: Prevents mechanical shock to regulator linkages by limiting the rotational speed of the servo, simulating the weight and friction of a real steam lever.

Servo End-Point Calibration: Independent CVs for Neutral (Closed), Max (Open), and Physical Travel limits to accommodate any servo/linkage geometry.

Whistle Zone Logic: Dedicates a specific rotational offset from neutral to actuate a steam whistle valve without admitting steam to the cylinders.

Jitter-Sleep Mode: Automatically cuts PWM signals to the servo when it hasn't moved for 2 seconds to eliminate "digital hum" and extend motor life.

4. Triple-Vector Safety Watchdogs
Dry-Boil Protection: Monitors the boiler temperature and triggers a shutdown if it exceeds 110°C (indicating the boiler has run dry).

Steam Quality Guard: Monitors the superheater temperature to protect gaskets and pipes from exceeding 250°C.

Silicon Thermal Safety: Monitors the TinyPICO’s internal temperature to prevent logic-bay overheating (75°C threshold).

Signal Failsafe: Detects lost DCC signals or radio links and initiates a safe stop after a user-defined timeout.

Brownout Monitoring: Detects track power drops and secures the locomotive using supercapacitor reserves before the logic dies.

5. Emergency Shutdown Protocol
Prioritized Power Cut: Instantly kills heater elements to stop steam generation.

Mechanical Distress Sequence: Moves the regulator to a "Distress Whistle" position for 5 seconds to vent excess pressure and alert the operator.

Secured Valve State: Ensures the regulator returns to a hard neutral position before the system enters deep sleep.

"Black Box" Event Capture: Saves the final 20 events from RAM into a persistent flash log for post-mortem diagnostics.

6. Resource & Memory Management
Threshold-Based Garbage Collection: Manually triggers memory cleanup at the end of every loop if free RAM falls below 60KB, preventing "Stop-the-World" stalls during motion.

Jitter-Free Timing: Dynamically adjusts loop sleep times to maintain a rock-solid 50Hz (20ms) cycle frequency for consistent servo signals.

Flash Stewardship: Protects internal storage by pushing telemetry only via BLE/USB and reserving flash writes exclusively for critical errors or config changes.

7. Observability & Diagnostics
Live BLE Telemetry: Streams real-time Speed, PSI, Temperature, and Servo Duty cycles to a smartphone or computer without interrupting control logic.

USB Serial Debugging: Provides a "Black Box" log dump and real-time status updates for bench testing.

Error Logging: Maintains a structured JSON log of failures to help troubleshoot mechanical or electrical issues.
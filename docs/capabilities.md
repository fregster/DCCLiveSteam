## Sensor Fallback & Degraded Modes

The system automatically detects missing or failed sensors and gracefully degrades control logic to maintain safe operation:

- **Speed Sensor (Encoder) Optional:**
	- If the speed sensor is unavailable or fails, the SpeedManager automatically reverts to direct throttle mode (regulator % from DCC), regardless of CV52 setting. Cruise control is disabled, but the locomotive remains controllable.
- **Pressure Sensor Optional:**
	- If the pressure sensor is unavailable or fails, the PressureManager skips pressure-based PID and superheater staging. Boiler and superheater are controlled by temperature only, using conservative fallback logic. The mechanical safety valve provides ultimate overpressure protection.
- **Temperature Sensors Required:**
	- If any temperature sensor fails, the system will always initiate a safety shutdown. No fallback is permitted for thermal safety.

Sensor health is checked at startup and periodically at runtime. Degraded mode is reported via telemetry and status LEDs.
## Speed Control Mode (CV52)

Allows the user to select between two speed control behaviours:

- **CV52 = 1 (default):** Feedback speed control (cruise control). DCC speed sets the target speed, and the regulator is automatically managed to reach and maintain that speed using a feedback loop.
- **CV52 = 0:** Direct throttle mode. DCC speed command sets the regulator (throttle) position directly, bypassing the feedback loop. This is similar to manual throttle control.

This feature is safety-critical for prototypical operation and user flexibility. See CV.md for configuration details.
Here is the comprehensive list of capabilities for the ESP32 live steam locomotive control system, formatted for your project documentation.

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
Live BLE Telemetry: Streams real-time speed, pressure (kPa; PSI in brackets), temperature, and servo duty cycles to a smartphone or computer without interrupting control logic.

USB Serial Debugging: Provides a "Black Box" log dump and real-time status updates for bench testing.

Error Logging: Maintains a structured JSON log of failures to help troubleshoot mechanical or electrical issues.
# Implemented Features

This directory contains documentation for **completed and deployed** features of the ESP32 Live Steam Locomotive Controller. Each feature has two documentation files:

---

## Documentation Structure

### Technical Documents (`*-technical.md`)
**Audience:** Developers, maintainers, advanced users  
**Contents:**
- Architecture and design decisions
- Implementation details and algorithms
- Code examples and timing analysis
- Configuration variables (CVs)
- Testing and validation
- Performance metrics
- Known limitations and future enhancements

### Capabilities Documents (`*-capabilities.md`)
**Audience:** End users, operators, hobbyists  
**Contents:**
- Plain language explanation of what the feature does
- Why it matters for safe operation
- How to use it
- Real-world examples
- Troubleshooting tips
- Safety notes

---

## Implemented Features

### Emergency Shutdown System
**Status:** Production (v1.0.0)  
**Safety-Critical:** YES

- [emergency-shutdown-technical.md](emergency-shutdown-technical.md) - 6-stage shutdown sequence, timing analysis, fault triggers
- [emergency-shutdown-capabilities.md](emergency-shutdown-capabilities.md) - What happens during shutdown, recovery procedures, safety features

**What it does:** Automatically secures locomotive when faults detected (overheating, signal loss, power failure) using graduated sequence: heaters off → whistle → log save → regulator close → deep sleep.

---

### Non-Blocking BLE Telemetry
**Status:** Production (v1.0.0)  
**Performance-Critical:** YES

- [nonblocking-telemetry-technical.md](nonblocking-telemetry-technical.md) - Queue-based architecture, timing analysis, packet format
- [nonblocking-telemetry-capabilities.md](nonblocking-telemetry-capabilities.md) - How to connect, interpret data, troubleshoot BLE

**What it does:** Wireless real-time monitoring of velocity, pressure, temperatures, servo position via Bluetooth. Non-blocking design ensures telemetry never interferes with 50Hz control loop.

---

### Sensor Failure Graceful Degradation
**Status:** Production (v1.1.0)  
**Safety-Critical:** YES

- [sensor-degradation-technical.md](sensor-degradation-technical.md) - Sensor health tracking, 3-state watchdog (NOMINAL/DEGRADED/CRITICAL), linear deceleration algorithm, CV configuration
- [sensor-degradation-capabilities.md](sensor-degradation-capabilities.md) - Single sensor failure handling, automatic speed reduction, distress signal, troubleshooting guide

**What it does:** When a sensor fails (disconnected, out-of-range), system smoothly decelerates locomotive over 10-20 seconds instead of emergency stop. Gives operators time to react, prevents derailment of loaded consists. Uses CV84 (enable/disable), CV87 (decel rate), CV88 (timeout).

**Key Improvement:** Transient glitches handled gracefully via sensor value caching. Single sensor failure enters DEGRADED mode with controlled slowdown. Multiple simultaneous failures trigger immediate emergency shutdown for maximum safety.

---

### BLE Configuration Variable (CV) Updates
**Status:** Production (v1.2.0)  
**User Experience-Critical:** YES

- [ble-cv-update-technical.md](ble-cv-update-technical.md) - BLE RX infrastructure, CV validation logic, command processing, timing analysis, 22 comprehensive unit tests
- [ble-cv-update-capabilities.md](ble-cv-update-capabilities.md) - Over-the-air CV updates, mobile app usage, real-world tuning examples, troubleshooting guide

**What it does:** Change any CV wirelessly via Bluetooth using simple text commands (`CV32=20.0`). No USB cable, no bench programming, no powered track required. Track-side tuning during operating sessions, fleet management, real-time parameter adjustment while monitoring telemetry. Validated against hardcoded safety bounds (23 CVs), atomic updates, persistent storage, audit trail logging.

**Key Improvement:** Transforms configuration workflow from 15-20 minutes (USB connect, file edit, upload) to <1 second (BLE command). Enables real-time tuning while locomotive running - send command, observe telemetry, iterate. Ideal for operating sessions, pressure tuning, servo response adjustment, seasonal thermal limit changes.

---

### Safety-First Watchdog Logic
**Status:** Production (v1.0.0)  
**Safety-Critical:** YES

- [safety-watchdog-technical.md](safety-watchdog-technical.md) - Multi-vector monitoring, thermal/signal/health checks, timing analysis
- [safety-watchdog-capabilities.md](safety-watchdog-capabilities.md) - Understanding watchdog alerts, configuration tuning, troubleshooting

**What it does:** Continuous monitoring of three safety vectors: thermal limits (boiler/superheater/controller), signal integrity (DCC/power timeouts), system health (memory/loop timing). Automatically triggers 6-second emergency shutdown sequence if any fault detected.

---

### Slew-Rate Limited Motion Control
**Status:** Production (v1.0.0)  
**Performance-Critical:** YES

- [motion-control-technical.md](motion-control-technical.md) - Velocity filtering algorithm, servo timing, CV49 configuration
- [motion-control-capabilities.md](motion-control-capabilities.md) - How throttle movement works, adjusting smoothness, servo lifespan

**What it does:** Smooth regulator (throttle) motion via velocity limiting configured by CV49 (travel time). Prevents mechanical stress on servo, provides realistic motion, extends servo lifespan 5-10x versus snap moves.

---

### Prototypical Physics Engine
**Status:** Production (v1.0.0)  
**Accuracy-Critical:** YES

- [physics-engine-technical.md](physics-engine-technical.md) - DCC-to-velocity conversion pipeline, pressure compensation, scale conversion
- [physics-engine-capabilities.md](physics-engine-capabilities.md) - Understanding speed control, configuring for your scale, real-world examples

**What it does:** Converts DCC speed commands (0-127) and boiler pressure into accurate model scale velocity. Uses CV39 (prototype speed) and CV40 (scale ratio) to ensure model operates at prototypically-scaled speeds. Automatically reduces speed when boiler pressure drops.

---

## Document Lifecycle

### When Features Enter This Directory

Features are moved from `docs/copilot-wip/` to `docs/implemented/` when:
1. ✅ Implementation complete and merged
2. ✅ All tests passing
3. ✅ Deployed to production (v1.x.x release)
4. ✅ Validated in real-world use

**What Gets Created:**
- ✅ `feature-name-technical.md` - How it works (architecture, implementation, testing)
- ✅ `feature-name-capabilities.md` - What it does (user guide, examples, troubleshooting)
- ✅ Entry in this README.md

**What Does NOT Get Moved:**
- ❌ WIP verification documents - delete after info extracted to technical/capabilities docs
- ❌ Implementation tracking documents - delete after info extracted
- ❌ Phase summaries - delete after info extracted to CHANGELOG.md
- ❌ Session reports - delete after info extracted to feature docs
- ❌ Progress tracking documents - delete after features documented

### Documentation Requirements

Before moving to `implemented/`:
1. Create technical document explaining **how it works**
2. Create capabilities document explaining **what it does**
3. Ensure both documents are complete and accurate
4. Cross-reference with user guides (CV.md, FUNCTIONS.md, TROUBLESHOOTING.md)

---

## Related Documentation

### User Guides (Root Level)
- [docs/CV.md](../CV.md) - Configuration variable reference
- [docs/FUNCTIONS.md](../FUNCTIONS.md) - Complete API reference
- [docs/DEPLOYMENT.md](../DEPLOYMENT.md) - Installation guide
- [docs/TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - Fault diagnosis
- [docs/capabilities.md](../capabilities.md) - System overview

### Development Documents
- [docs/plans/](../plans/) - Future features and architectural decisions
- [docs/copilot-wip/](../copilot-wip/) - Active work-in-progress tracking
- [docs/external-references/](../external-references/) - Standards and specifications

---

## Future Features (Not Yet Implemented)

The following features are planned but not yet documented here:

1. **CV Programming Track Support** - NMRA service mode programming
2. **Long Address Support** - 14-bit DCC addresses (128-9999)
3. **Sound Integration** - DCC function triggers for external sound module
4. **Smoke Generator Control** - PWM control via F6 function
5. **Slip Detection** - Compare encoder velocity to DCC speed command
6. **Advanced PID Tuning** - User-configurable PID coefficients
7. **Over-the-Air Updates** - BLE firmware upload
8. **Web Interface** - HTTP server for configuration
9. **SD Card Logging** - Extended event logging
10. **Multi-Locomotive Support** - Control multiple locomotives

These will receive documentation here when implemented in future versions.

---

## Feature Statistics

**Implemented Features:** 5
- Emergency Shutdown System (v1.0.0)
- Non-Blocking BLE Telemetry (v1.0.0)
- Safety-First Watchdog Logic (v1.0.0)
- Slew-Rate Limited Motion Control (v1.0.0)
- Prototypical Physics Engine (v1.0.0)

**Total Documentation Files:** 10 (5 features × 2 documents each)
- 5 technical documents (architecture, implementation, testing)
- 5 capabilities documents (user guides, examples, troubleshooting)

**Planned Features:** 10
- Feature implementation order depends on user prioritisation

---

## Contribution Guidelines

### Adding New Feature Documentation

When completing a new feature:

1. **Create technical document:**
   ```markdown
   # Feature Name - Technical Implementation
   
   **Component:** [Subsystem name]
   **Module:** app/[module].py
   **Version:** [X.Y.Z]
   **Safety/Performance-Critical:** YES/NO
   
   ## Overview
   [High-level architecture]
   
   ## Implementation
   [Code examples, algorithms]
   
   ## Testing
   [Test coverage, validation]
   
   ## Configuration
   [CVs, parameters]
   
   ## Performance Metrics
   [Timing, memory usage]
   ```

2. **Create capabilities document:**
   ```markdown
   # Feature Name
   
   ## What It Is
   [Simple explanation]
   
   ## What It Does
   [User-facing behavior]
   
   ## Why It Matters
   [Benefits, safety considerations]
   
   ## How to Use It
   [Step-by-step instructions]
   
   ## Real-World Example
   [Practical scenario]
   
   ## Troubleshooting
   [Common issues]
   
   ## Safety Notes
   [Warnings, precautions]
   ```

3. **Update this README** with new feature entry

4. **Cross-reference** in user guides (CV.md, FUNCTIONS.md, etc.)

---

## Maintenance

### Document Ownership
- **Technical docs:** Maintained by developers
- **Capabilities docs:** Maintained for end users (plain language)
- **Both:** Updated when feature changes in new releases

### Version History
Each document includes version number matching the release where feature was added or last significantly changed.

---

**Directory Created:** 28 January 2026  
**Last Updated:** 28 January 2026  
**Maintained By:** ESP32 Live Steam Project

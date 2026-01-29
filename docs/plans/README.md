# Planning Documents

This folder contains forward-looking planning documents for future features, architectural decisions, and design proposals.

**These are permanent references** that guide implementation and track design decisions. Implementation plans created during planning sessions are moved here after planning completes.

---

## Purpose

Planning documents are used to:
- Propose new features before implementation
- Document architectural design decisions
- Plan performance improvements
- Track technical debt and refactoring needs
- Analyze trade-offs between implementation approaches
- Guide multi-phase feature implementation

## Document Types

### Implementation Plans
Multi-phase feature designs ready for development:
- Executive summary
- Detailed implementation phases (1-5)
- Code examples and architecture diagrams
- Configuration variables (CVs) required
- Testing strategy (unit + integration tests)
- Safety considerations and failsafes
- Performance budget analysis
- Implementation checklist
- Known constraints and future enhancements

**When created:** Completed during planning session, moved from WIP  
**When implemented:** Serves as development roadmap  
**When complete:** Referenced by technical documentation in `docs/implemented/`

### Feature Proposals
Document new capabilities or enhancements:
- Problem statement (what need does this solve?)
- Proposed solution
- Implementation approach
- Testing strategy
- Safety considerations (for safety-critical features)

### Architecture Documents
Design decisions for major subsystems:
- Component interaction diagrams
- Data flow analysis
- Interface definitions
- Performance requirements
- Memory constraints (ESP32 RAM limits)

### Performance Plans
Optimization strategies:
- Profiling results
- Bottleneck analysis
- Proposed optimizations
- Benchmark targets

## Current Implementation Plans

### v1.1.0 - Communication & Configuration
- **BLE_CV_UPDATE_IMPLEMENTATION.md** - Over-the-air CV updates via Bluetooth
  - 4 phases: RX infrastructure, command parser, main loop integration, telemetry feedback
  - Status: Ready for Phase 1 implementation
  - Effort: ~20 hours

### v1.2.0 - Safety & Reliability
- **SENSOR_FAILURE_GRACEFUL_DEGRADATION.md** - Graceful handling of sensor failures
  - 5 phases: Health tracking, watchdog modes, controlled deceleration, distress signal, shutdown
  - Status: Ready for Phase 1 implementation
  - Effort: ~40 hours
  - Safety-critical: YES (prevents train derailment on load, adds distress signal)

## Naming Convention

Use descriptive names (no date prefix—implementation plans use full names):
- `FEATURE_NAME_IMPLEMENTATION.md` - Implementation plans (multi-phase, ready to develop)
- `FEATURE_NAME_PROPOSAL.md` - Feature proposals (under consideration)
- `ARCHITECTURE_TOPIC.md` - Architecture decisions
- `PERFORMANCE_IMPROVEMENT.md` - Optimization plans

## Status Tracking

Mark document status at the top:
- **Status: PROPOSED** - Under consideration
- **Status: PLANNING** - In active planning (in WIP, not here)
- **Status: APPROVED** - Ready for implementation (moved to plans/)
- **Status: IN_PROGRESS** - Under development (tracked in WIP during active work)
- **Status: COMPLETE** - Implemented and merged (moved to `docs/implemented/`)

- **Status: IN PROGRESS** - Currently being implemented
- **Status: COMPLETED** - Implemented (move to copilot-wip/)
- **Status: REJECTED** - Not pursuing (document why)

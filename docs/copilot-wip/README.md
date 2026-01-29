# Copilot Work-In-Progress (WIP)

**⚠️ CRITICAL:** This folder is **EXCLUSIVELY for temporary session documents** while Copilot is actively working on features. **All permanent planning and implementation documents belong in `docs/plans/`.**

This folder contains **active development tracking documents only**. These are **NOT user-facing documents**—they track ongoing work during development sessions and are deleted when work completes.

---

## Folder Purpose & Lifecycle

### ✅ What BELONGS in `docs/copilot-wip/`
- **Session notes** - Temporary tracking during active development
- **Progress tracking** - "Currently working on X", "Need to fix Y"
- **Debug logs** - Temporary troubleshooting documents
- **Verification documents** - Phase completion checklists for current session
- **Short-term planning** - Notes being actively refined in current session

**Lifespan:** 1 working session (hours to days). **Deleted when feature complete.**

### ❌ What Does NOT Belong in `docs/copilot-wip/`
- **Implementation plans** → `docs/plans/` (multi-phase designs, technical architecture)
- **Feature designs** → `docs/plans/` (detailed specifications, testing strategies)
- **Architectural decisions** → `docs/plans/` (system design, CV specifications)
- **Session summaries** → Extract to feature docs, then delete
- **Phase completion reports** → Extract to CHANGELOG.md, then delete

### Where Documents GO After Active Development Completes

1. **Implementation Plans** (multi-phase designs)
   - Created in WIP during planning
   - **MOVE to `docs/plans/`** immediately after planning complete
   - Rationale: Plans are forward-looking, meant to guide development
   
2. **Completed Features** (after development + deployment)
   - Implementation moved to codebase (app/ directory)
   - **CREATE in `docs/implemented/`**: feature-name-technical.md + feature-name-capabilities.md
   - **DELETE from WIP**: All session notes, verification docs, progress tracking
   - Rationale: Completed features documented for users and maintainers

---

## Document Routing Decision Tree

```
New document needed?
    ↓
Is it a **multi-phase implementation plan** 
or **architectural design**?
    ├─ YES → `docs/plans/` (permanent)
    ├─ NO → Continue...
    ↓
Is it **temporary session tracking** 
(notes, progress, debug)?
    ├─ YES → `docs/copilot-wip/` (delete when done)
    ├─ NO → Continue...
    ↓
Is it a **completed and deployed feature**?
    ├─ YES → `docs/implemented/` (permanent)
    ├─ NO → Continue...
    ↓
Is it **user-facing documentation** 
(CV reference, capabilities, troubleshooting)?
    └─ YES → `docs/` root level (permanent)
```

---

## Current Contents

### Active Session Documents (Temporary)
*Empty - no active development in progress*

---

## Document Lifecycle (Complete Flowchart)

### Phase 1: Initial Planning (Active, in WIP)
```
Session starts → Create implementation plan → Refine daily
↓ (When plan complete)
MOVE to docs/plans/ (permanent forward-looking reference)
DELETE from WIP (no longer active session doc)
```

### Phase 2: Active Development (Active, in WIP)
```
Development session → Create session notes/progress tracking
↓ (Multiple sessions)
Update WIP documents daily during development
↓ (When feature complete)
DELETE WIP documents (extract info to code comments & tests)
```

### Phase 3: Feature Complete (Move to Implemented)
```
Code merged ✅
All tests passing ✅
Deployed to release ✅
    ↓
Create `feature-name-technical.md` → `docs/implemented/`
Create `feature-name-capabilities.md` → `docs/implemented/`
Update `docs/implemented/README.md`
DELETE all WIP documents
```

---

## Completed Features Documented (in `docs/implemented/`)

**Emergency Shutdown System:**
- ✅ emergency-shutdown-technical.md
- ✅ emergency-shutdown-capabilities.md

**Non-Blocking BLE Telemetry:**
- ✅ nonblocking-telemetry-technical.md
- ✅ nonblocking-telemetry-capabilities.md

**Deleted WIP tracking documents:**
- ❌ EMERGENCY_SHUTDOWN_VERIFICATION.md - info extracted to technical/capabilities docs
- ❌ ESTOP_IMPLEMENTATION.md - info extracted to technical/capabilities docs
- ❌ NONBLOCKING_TELEMETRY.md - info extracted to technical/capabilities docs
- ❌ PARALLEL_LOG_OPTIMIZATION.md - info extracted to technical/capabilities docs
- ❌ PHASE2_SAFETY_AUDIT.md - tracking document, info now in CHANGELOG.md
- ❌ PHASE4_COMPLETION.md - tracking document, info now in CHANGELOG.md
- ❌ SESSION_COMPLETION.md - tracking document, info now in feature docs

**Documentation Format:**
Each completed feature has exactly TWO files:
- `feature-name-technical.md` - How it works (for developers)
- `feature-name-capabilities.md` - What it does (for users)

---

## Purpose

These WIP documents help:
- **Track active development** across sessions
- **Plan future features** before implementation
- **Record design decisions** during development
- **Maintain context** when resuming work

**⚠️ These are temporary documents** - they should graduate to proper documentation once complete.

---

## Not for End Users

These documents are **internal development artifacts**. End users should reference:
- [docs/CV.md](../CV.md) - Configuration reference
- [docs/FUNCTIONS.md](../FUNCTIONS.md) - API documentation
- [docs/DEPLOYMENT.md](../DEPLOYMENT.md) - Installation guide
- [docs/TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - Fault diagnosis
- [docs/implemented/](../implemented/) - Completed feature documentation  
- `docs/capabilities.md` - Feature list

## Adding New WIP Documents

When creating new tracking documents:
- Use clear, descriptive names indicating content type
- Include date stamps for time-sensitive tracking
- Update this README with a brief description
- Archive to this folder when moving on to new work

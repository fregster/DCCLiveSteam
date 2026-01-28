# Copilot Work-In-Progress

This folder contains **active development tracking documents**. These are **not user-facing documents**—they track ongoing work during development sessions.

**⚠️ Important:** Once features are complete and deployed, their documentation should be moved to `docs/implemented/` with proper technical and capabilities documents.

---

## Current Contents

### Active Planning Documents
- **TODO_IMPROVEMENTS.md** - Pending improvement tasks and future work

---

## Document Lifecycle

### 1. Active Development (HERE)
- Documents created during feature development
- Progress tracking and session notes
- Planning documents for future features

### 2. Feature Completion → Move to `docs/implemented/`
When a feature is complete:
1. ✅ Implementation merged and tested
2. ✅ All unit tests passing
3. ✅ Feature deployed in release
4. ⚠️ **MUST:** Create two new documents in `docs/implemented/`:
   - `feature-name-technical.md` - How it works (architecture, code, testing)
   - `feature-name-capabilities.md` - What it does (user guide, examples, troubleshooting)
5. ⚠️ **MUST:** Move WIP document from here to `docs/implemented/` for historical reference
6. ⚠️ **MUST:** Update `docs/implemented/README.md` with new feature entry

### 3. Historical Reference (`docs/implemented/`)
- Completed feature documentation
- Technical implementation details
- User-facing capabilities guides

---

## Completed Features Documented

The following features have been properly documented in `docs/implemented/`:

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

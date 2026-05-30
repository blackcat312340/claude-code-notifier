# Requirements: Claude Code Notifier

**Defined:** 2026-05-29
**Core Value:** When Claude Code needs you or finishes waiting for you, you should know immediately without watching the terminal.

## v1 Requirements

### Hook Integration

- [ ] **HOOK-01**: User can install notifier-managed Claude Code hooks into the user-level Claude settings without deleting unrelated existing settings
- [ ] **HOOK-02**: User can uninstall notifier-managed Claude Code hooks cleanly from the user-level Claude settings
- [ ] **HOOK-03**: Hook commands can receive Claude Code event payloads and forward them into the notifier runtime with session and project metadata

### Session Tracking

- [ ] **SESS-01**: Notifier can track Claude Code sessions across all local projects by session identifier and working directory
- [ ] **SESS-02**: Notifier can derive a stable project display name from the hook payload for notifications and event history
- [ ] **SESS-03**: Notifier can record a recent local event history for debugging and operator trust

### Attention Notifications

- [ ] **ATTN-01**: User receives a Windows desktop notification when Claude Code raises a permission-related notification
- [ ] **ATTN-02**: User receives a Windows desktop notification when Claude Code becomes idle and is waiting for further input
- [ ] **ATTN-03**: Each notification includes the project name and reminder type

### Tray Experience

- [ ] **TRAY-01**: User can run the notifier as a background tray application
- [ ] **TRAY-02**: User can view recent notifier events from the tray surface
- [ ] **TRAY-03**: User can see whether hook integration is currently installed from the tray surface
- [ ] **TRAY-04**: User can jump from the tray surface back to the related project or session context for a recent reminder

### Abnormal-State Detection

- [ ] **ANOM-01**: Notifier can detect and notify when a tracked Claude session has been inactive for more than 5 minutes while still appearing active
- [ ] **ANOM-02**: Notifier can emit an error-like reminder when hook processing or session monitoring detects an abnormal state worth user review
- [ ] **ANOM-03**: Notifier suppresses duplicate reminders within a short cooldown window for the same session and category

## v2 Requirements

### Navigation

- **NAV-02**: User can click a desktop notification to open the relevant tray detail or project

### Remote Delivery

- **REM-01**: User can forward selected reminders to a remote channel such as Telegram or email
- **REM-02**: User can configure different delivery rules per reminder type

### Configuration

- **CONF-01**: User can change inactivity thresholds from the app UI
- **CONF-02**: User can enable or disable specific reminder categories per project

## Out of Scope

| Feature | Reason |
|---------|--------|
| Auto-approving Claude tool permissions | Conflicts with the notifier-only product role |
| Full transcript viewer or replay UI | Adds substantial scope beyond reminder validation |
| Cross-platform desktop support in v1 | Windows-first delivery is the current constraint |
| Web dashboard or cloud sync | Not needed to validate the local reminder workflow |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| HOOK-01 | Phase 1 | Verified |
| HOOK-02 | Phase 5 | Pending |
| HOOK-03 | Phase 1 | Verified |
| SESS-01 | Phase 1 | Verified |
| SESS-02 | Phase 1 | Verified |
| SESS-03 | Phase 3 | Verified |
| ATTN-01 | Phase 2 | Verified |
| ATTN-02 | Phase 2 | Verified |
| ATTN-03 | Phase 2 | Verified |
| TRAY-01 | Phase 2 | Verified |
| TRAY-02 | Phase 3 | Verified |
| TRAY-03 | Phase 5 | Pending |
| TRAY-04 | Phase 3 | Verified |
| ANOM-01 | Phase 4 | Pending |
| ANOM-02 | Phase 4 | Pending |
| ANOM-03 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0

---
*Requirements defined: 2026-05-29*
*Last updated: 2026-05-29 after initial definition*

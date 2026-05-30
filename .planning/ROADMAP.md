# Roadmap: Claude Code Notifier

## Overview

- Project mode: Vertical MVP
- Total phases: 5
- v1 requirements mapped: 16 of 16

### Phase 1: Hook Event Backbone

**Goal:** Establish a supported Claude Code hook ingestion path that can identify sessions and projects across the local machine.
**Mode:** mvp
**Requirements:** HOOK-01, HOOK-03, SESS-01, SESS-02
**UI hint:** no
**Plans:** 2 plans
**Success Criteria**:

1. A notifier-managed hook configuration can be generated and installed into user-level Claude settings without deleting unrelated config
2. Hook events can reach a notifier entrypoint with normalized session and project metadata
3. The system can show that multiple sessions from different project directories are distinguishable

Plans:
**Wave 1**

- [x] 01-01-PLAN.md -- Walking Skeleton + Event Pipeline (HOOK-03, SESS-01, SESS-02)

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 01-02-PLAN.md -- Hook Config Installation (HOOK-01)

### Phase 2: First Useful Reminders

**Goal:** Deliver the first end-to-end Windows reminder experience for attention-worthy Claude Code events.
**Mode:** mvp
**Requirements:** ATTN-01, ATTN-02, ATTN-03, TRAY-01
**UI hint:** yes
**Success Criteria**:

1. A background tray process can run reliably on Windows
2. Permission-related hook events trigger a Windows desktop notification
3. Idle-waiting events trigger a Windows desktop notification
4. Notifications include the project name and reminder type

### Phase 3: Operator Trust Surface

**Goal:** Give the developer enough local visibility to trust and inspect what the notifier is doing.
**Mode:** mvp
**Requirements:** SESS-03, TRAY-02, TRAY-04
**UI hint:** yes
**Success Criteria**:

1. Recent events are stored locally with timestamps and session/project context
2. The tray surface exposes a recent-event list or equivalent inspection view
3. A developer can understand why a notification fired without reading raw hook payloads
4. A developer can navigate from the tray surface back to the relevant project or session context

### Phase 4: Abnormal-State Detection

**Goal:** Extend the notifier beyond direct hook notifications by detecting stalled or abnormal Claude sessions.
**Mode:** mvp
**Requirements:** ANOM-01, ANOM-02, ANOM-03
**UI hint:** yes
**Success Criteria**:

1. The notifier can track session heartbeats or last-seen activity well enough to detect 5-minute inactivity
2. Inactivity reminders avoid spamming duplicate alerts for the same session
3. At least one error-like abnormal state path produces a user-facing reminder

### Phase 5: Safe Hook Lifecycle

**Goal:** Make the notifier safe to adopt by completing reversible integration and visible integration status.
**Mode:** mvp
**Requirements:** HOOK-02, TRAY-03
**UI hint:** yes
**Success Criteria**:

1. Users can uninstall notifier-managed hooks cleanly
2. The tray UI reports whether hooks are currently installed
3. Install/uninstall behavior is idempotent and documented

## Phase Details

### Phase 1 Notes

- Build the event schema and session registry first
- Keep hook execution fast; defer heavy work to a resident process

### Phase 2 Notes

- This is the first phase that should feel useful day to day
- Prefer notification reliability over visual polish

### Phase 3 Notes

- Trust comes from visibility, not just raw functionality
- The tray should explain what happened recently

### Phase 4 Notes

- "Stuck" is heuristic; bias toward fewer false positives
- Cooldown and deduplication are mandatory

### Phase 5 Notes

- Hook lifecycle safety is part of the product, not just setup glue
- This phase should leave the tool easy to adopt and easy to back out

---
*Last updated: 2026-05-30 after phase 1 plan creation*

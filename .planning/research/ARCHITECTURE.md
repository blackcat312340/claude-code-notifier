# Architecture Research

## Proposed High-Level Shape

### 1. Hook Entry Layer

Claude Code invokes a small command on hook events. That command should do minimal synchronous work:

- Parse stdin JSON
- Identify the event name and project/session metadata
- Append or forward the event to the local notifier runtime
- Exit quickly so Claude Code is not delayed

### 2. Local Event Bus / Store

A long-running local notifier process receives hook events and maintains:

- Session registry
- Recent event log
- Last-seen timestamps for inactivity detection
- Reminder deduplication windows

### 3. Classifier Layer

Map raw hook events into product-level reminder categories:

- `needs_attention.permission`
- `needs_attention.input`
- `task_waiting.idle`
- `session_stop`
- `anomaly.error_like`
- `anomaly.inactive`

### 4. Notification Layer

Emit Windows desktop notifications with a normalized schema:

- Project name
- Reminder type
- Short body text
- Timestamp

### 5. Tray Surface

Expose running status and recent events from the background process. Notification clicks are not required in v1, so the tray surface is the primary inspection UI.

## Important Design Implications

- Hook commands must stay fast; background processing is safer than doing everything inline
- Inactivity detection probably needs a timer in the tray/background process, not a hook alone
- Error-like reminders may require combining hook outcomes with session stop patterns and local processing heuristics
- User-level hook install/uninstall should be idempotent and avoid clobbering unrelated Claude settings

---
*Last updated: 2026-05-29*

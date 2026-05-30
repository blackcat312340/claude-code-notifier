# Phase 2: First Useful Reminders - Context

**Gathered:** 2026-05-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver the first end-to-end Windows reminder experience: a tray application that runs silently in the background, receives classified events from the Phase 1 TCP pipeline, and fires Windows desktop notifications for attention-worthy Claude Code events.

**In scope:** Windows tray icon (presence indicator), desktop notifications for permission/idle/done events, 30s per-category cooldown, silent background process launched via `python -m notifier`.

**Out of scope:** Event history storage (Phase 3), tray inspection view (Phase 3), anomaly/stall detection (Phase 4), notification click actions (Phase 3+), auto-start on login (future phase), hook uninstall (Phase 5).
</domain>

<decisions>
## Implementation Decisions

### Tray & Notification Stack
- **D-01:** Tray library — **pystray**. Cross-platform (Windows/macOS/Linux), simple API (icon + menu + run), uses Pillow for icon images. Adds one dependency.
- **D-02:** Notification library — **winotify**. Modern Windows 10/11 toast notifications via WinRT. Supports title, body, icon, and actions. Clean Python API. Works without UWP/MSIX packaging.
- **D-03:** Tray icon — **minimal placeholder** for v1. Use pystray's built-in text/image rendering. No custom .ico file needed. Branding deferred to later.
- **D-04:** Notification format — **Title + body**. Title = project name (from session.project_name). Body = reminder type + brief context (e.g., "Permission needed — Claude wants to run npm install"). Satisfies ATTN-03 (project name + reminder type).

### Notification Rules
- **D-05:** Notified categories — **PERMISSION, IDLE, DONE**. ERROR events are logged but do not produce notifications (they indicate misconfiguration/unknown event types, not user-actionable alerts).
- **D-06:** Cooldown — **30 seconds** per (project_name, category) composite key. Prevents notification spam when Claude fires multiple hooks in rapid succession. Timer resets after each notification; no global rate limit.
- **D-07:** Click action — **None for v1**. Clicking dismisses the notification. Click-to-navigate deferred to Phase 3.

### Process Architecture
- **D-08:** Startup — **`python -m notifier`** launches the tray app directly. Replaces the Phase 1 TCP-server-only `__main__.py`. Single command, no flags needed.
- **D-09:** Event loop coexistence — **TCP server in daemon thread, pystray owns main thread**. The asyncio TCP server from Phase 1 runs in a background daemon thread. Pystray's blocking `run()` call owns the main thread. Thread-safe queue bridges incoming events from TCP thread to tray thread.
- **D-10:** Console window — **Silent (no console)**. Use `.pyw` extension or `pythonw.exe` to suppress console window on Windows. Tray icon is the only visible presence.
- **D-11:** Auto-start — **Manual start only for v1**. No startup folder integration, no registry entries. User runs `python -m notifier` when they want monitoring.

### Tray Menu Behavior
- **D-12:** Right-click menu — **Exit only**. Single "Exit" menu item that stops the TCP server and quits the tray. Full menu (status, recent events) deferred to Phase 3.
- **D-13:** Tooltip — **"Claude Code Notifier — Monitoring (N sessions)"** with live session count from the session registry. Updates as sessions connect/disconnect via the Phase 1 TCP server.

### Claude's Discretion
No areas deferred to Claude — all decisions explicitly captured.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project-Level
- `.planning/PROJECT.md` — Scope, constraints (Windows-first, desktop notifications, tray), key decisions
- `.planning/REQUIREMENTS.md` — Phase 2 requirements: ATTN-01 (permission notifications), ATTN-02 (idle notifications), ATTN-03 (project name + reminder type in notifications), TRAY-01 (background tray application)
- `.planning/ROADMAP.md` — Phase 2 success criteria: (1) background tray process, (2) permission event notifications, (3) idle event notifications, (4) notifications include project name + reminder type

### Phase 1 Artifacts
- `.planning/phases/01-hook-event-backbone/01-RESEARCH.md` — Dependency versions (Python 3.12.7, Typer 0.25.0), project structure conventions
- `.planning/phases/01-hook-event-backbone/01-CONTEXT.md` — Event taxonomy (D-01: 4 categories), session identity (D-04/D-05), IPC design (D-10/D-11/D-12)
- `.planning/phases/01-hook-event-backbone/SKELETON.md` — Architectural decisions (TCP localhost IPC, NDJSON, dataclass event schema)

### External
- pystray documentation: https://pystray.readthedocs.io/ — Tray icon API, menu building, event loop
- winotify documentation: https://github.com/versa-syahptr/winotify — Windows toast notification API
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`src/notifier/core/events.py`** — `EventCategory` enum (PERMISSION, IDLE, DONE, ERROR), `NotifierEvent` dataclass with `to_dict()`, `SessionInfo` with `project_name`. The notification subsystem reads event.category and event.session.project_name directly.
- **`src/notifier/core/session.py`** — `extract_session()` and `project_name()`. Session identity extraction already handles the composite key.
- **`src/notifier/server/tcp_server.py`** — `NotifierServer` class with asyncio TCP server and `session_registry` dict. Needs to run in daemon thread alongside pystray. The `_handle_client` method receives events — this is where notification dispatch hooks in.
- **`src/notifier/__main__.py`** — Currently delegates to `tcp_server.main()`. Will be replaced with tray launch logic.
- **`src/notifier/core/ipc.py`** — Constants (`NOTIFIER_HOST`, `NOTIFIER_PORT`) reused by the server.

### Established Patterns
- **Dataclass-based domain model** — `NotifierEvent`, `SessionInfo`, `SessionRecord` are dataclasses with `asdict()`. Continue this pattern for notification-related types.
- **Python 3.12+ stdlib preference** — Phase 1 used stdlib wherever possible (json, socket, asyncio, pathlib). Libraries only when they add real value.
- **pyproject.toml** — Single source for dependencies and entry points. Add pystray and winotify here.
- **Tests in `src/notifier/tests/`** — pytest with asyncio_mode=auto. New tests follow the same structure.

### Integration Points
- **`NotifierServer._handle_client`** — After `_update_session()`, insert notification dispatch: check category against D-05 rules, apply D-06 cooldown, call winotify.
- **`session_registry`** — Already tracks sessions by composite key. Tray tooltip reads `len(session_registry)` for live session count.
- **`__main__.py`** — Entry point changes from `tcp_server.main()` to tray launch with threaded TCP server.
</code_context>

<specifics>
## Specific Ideas

- Tray icon placeholder: pystray can render a simple colored square or text character ("N" for Notifier) using PIL Image. No icon file needed.
- Notification body examples:
  - PERMISSION: "Permission needed — Claude wants to run npm install"
  - IDLE: "Waiting for input — Claude is idle and awaiting further instructions"
  - DONE: "Task complete — Claude finished the current task"
- Cooldown tracking: simple in-memory dict `{(project_name, category): last_notification_timestamp}`. Checked before each notification; if < 30s since last, skip.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 2 scope.
</deferred>

---

*Phase: 2-First Useful Reminders*
*Context gathered: 2026-05-30*

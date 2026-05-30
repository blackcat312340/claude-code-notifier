# Phase 3: Operator Trust Surface - Context

**Gathered:** 2026-05-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Give the developer enough local visibility to trust and inspect what the notifier is doing. Add event history storage, a browseable tray menu, and event detail inspection.

**In scope:** Recent event storage (50-entry ring buffer), tray right-click menu with last 5 events, event detail popup window, project path display.

**Out of scope:** Persistent database storage (v1), notification click actions, remote delivery, full transcript viewer, session replay.
</domain>

<decisions>
## Implementation Decisions

### Event Storage
- **D-01:** Storage — **In-memory ring buffer** (`collections.deque`, maxlen=50). Zero dependencies, instant access. Events lost on restart — acceptable for v1 operator trust (SESS-03 requires "record", not "persist").
- **D-02:** Capacity — **50 events**. Enough context to understand recent notification behavior without overwhelming the menu or memory.

### Tray Menu
- **D-03:** Menu structure — **Last 5 events flat** at top (project name + category), separator, then Exit. Clicking an event opens its detail popup.
- **D-04:** Menu refresh — **Build on right-click**. pystray supports dynamic menu construction in the menu callback. No need for push updates — user right-clicks to inspect current state.

### Event Detail
- **D-05:** Detail display — **Popup window** using tkinter (stdlib, no new dependency). Shows: timestamp, project name, event category, hook event type, message content. Simple, one window at a time.
- **D-06:** Navigation (TRAY-04) — **Display project path** in the detail popup. User can see where the project lives and navigate manually. No auto-open — keeps it lightweight.

### Claude's Discretion
No areas deferred — all decisions captured.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project-Level
- `.planning/PROJECT.md` — Scope, constraints, key decisions
- `.planning/REQUIREMENTS.md` — Phase 3 requirements: SESS-03 (event history), TRAY-02 (tray event view), TRAY-04 (project navigation)
- `.planning/ROADMAP.md` — Phase 3 success criteria: (1) events stored with timestamps/context, (2) tray exposes event list, (3) understand why notification fired, (4) navigate to project

### Prior Phase Artifacts
- `.planning/phases/02-first-useful-reminders/02-SUMMARY.md` — Tray app architecture (NotifierTray, worker thread, queue)
- `.planning/phases/02-first-useful-reminders/02-CONTEXT.md` — Phase 2 decisions (D-12 tray menu, D-13 tooltip)
- `.planning/phases/01-hook-event-backbone/01-SUMMARY.md` — Event schema (NotifierEvent fields, EventCategory)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`src/notifier/tray/app.py`** — `NotifierTray` class. Phase 3 extends `_create_menu()` to include event list items and `_patch_server_handler()` to store events in the ring buffer.
- **`src/notifier/core/events.py`** — `NotifierEvent` dataclass with all fields needed for detail display (timestamp, category, session.project_name, hook_event_name, message).
- **`src/notifier/server/tcp_server.py`** — `_update_session` already hooked; Phase 3 extends the hook to also push into the event ring buffer.

### Integration Points
- **`NotifierTray._patch_server_handler()`** — currently puts events on notify queue. Extend to also append to `self.event_history` deque.
- **`NotifierTray._create_menu()`** — currently returns single "Exit" MenuItem. Extend to dynamically build menu with event items.
- **tkinter** — stdlib, no new dependency. Used for detail popup window. Lightweight Text/Label widget approach.

### Established Patterns
- **pystray dynamic menus** — pystray supports callable menus (`pystray.Menu(lambda: build_menu())`) for dynamic content. Use this for right-click refresh (D-04).
</code_context>

<specifics>
## Specific Ideas

- Ring buffer: `collections.deque(maxlen=50)` on `NotifierTray` instance. Append on each event.
- Menu items: "my-project — permission (1m ago)", "notifier — done (3m ago)", etc. Click → open detail popup.
- Detail popup: tkinter `Toplevel` with Labels showing timestamp, project, category, type, message, path. "Close" button at bottom.
- Path display: show the full `cwd` path so user can copy/paste or navigate manually.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 3 scope.
</deferred>

---

*Phase: 3-Operator Trust Surface*
*Context gathered: 2026-05-30*

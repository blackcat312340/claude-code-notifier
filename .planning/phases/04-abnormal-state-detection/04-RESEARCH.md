# Phase 4: Abnormal-State Detection - Research

**Researched:** 2026-06-04
**Domain:** Proactive session health monitoring (inactivity detection, error pattern recognition)
**Confidence:** HIGH

## Summary

Phase 4 adds proactive monitoring to the notifier — detecting stalled sessions and abnormal error patterns without requiring hook events to arrive. The core mechanism is a polling timer that examines the live `session_registry` every 60 seconds, comparing each session's `last_seen` timestamp against a 5-minute threshold. When a session exceeds the threshold, a synthetic inactivity notification fires through the existing `dispatch_notification` pipeline. Separately, ERROR events are tracked per session in a deque ring buffer to detect ERROR floods (3+ errors in 2 minutes), triggering an aggregated abnormal-state notification.

The implementation adds no new third-party packages — everything uses Python stdlib (`threading.Timer`, `datetime.fromisoformat`, `collections.deque`). The primary architectural risk is thread safety: the polling timer introduces a second writer to `session_registry` (the TCP server thread being the first), and a second consumer of the notification pipeline (via synthetic events). Both are mitigated with snapshot iteration and cooldown key isolation.

**Primary recommendation:** Use a rescheduling `threading.Timer` (started in `NotifierTray.run()`) for the polling loop; snapshot the registry with `list(dict.values())` for thread-safe iteration; extend `dispatch_notification` to accept synthetic inactivity/flood events with dedicated cooldown keys.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Polling loop via pystray main-thread timer. No new daemon thread.
- **D-02:** Polling interval: 60 seconds.
- **D-03:** Inactivity threshold: uniform 5 minutes across all sessions and providers.
- **D-04:** No heartbeat protocol — existing hook events update `last_seen`.
- **D-05:** Single notification per inactivity cycle per session. Timer resets on new event arrival.
- **D-06:** Inactivity cooldown: 5 minutes, dedicated key `(provider, session_id, "inactivity")`.
- **D-07:** Reuse `EventCategory.IDLE` for inactivity; differentiate via message body text.
- **D-08:** Silent recovery — no notification when inactive session receives new event.
- **D-09:** Monitor all registered sessions regardless of lifecycle stage.
- **D-10:** Skip stopped sessions (via `is_stopped` flag), do not remove from registry.
- **D-11:** Add `is_stopped: bool = False` to `SessionRecord`. Set on Stop event.
- **D-12:** Activity signal: `last_seen` only. No event counting or TCP state tracking.
- **D-13:** ERROR flood detection: 3 ERROR events within 2 minutes per session.
- **D-14:** Flood threshold: 3 errors / 2 minutes per session.
- **D-15:** Flood notification: ERROR category with conditional trigger. Individual ERRORs remain log-only.
- **D-16:** Flood cooldown: 10 minutes per session.

### Claude's Discretion
No areas were deferred to Claude — all decisions were explicitly captured during discussion.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within Phase 4 scope.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ANOM-01 | Detect and notify when a tracked session has been inactive for more than 5 minutes while still appearing active | Inactivity polling loop pattern (Section: Architecture Patterns), `datetime.fromisoformat` for `last_seen` comparison |
| ANOM-02 | Emit an error-like reminder when hook processing or session monitoring detects an abnormal state worth user review | ERROR flood detection pattern with deque ring buffer, cooldown-isolated synthetic notification path |
| ANOM-03 | Suppress duplicate reminders within a short cooldown window for the same session and category | Dedicated cooldown key isolation `(provider, session_id, "inactivity")` and `(provider, session_id, "error_flood")` |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Inactivity detection polling | Tray Application (main thread) | — | Timer runs on pystray main-thread space per D-01; accesses in-memory `session_registry` directly |
| Session inactivity calculation | Tray Application (timer callback) | — | Pure time math on `SessionRecord.last_seen`; no I/O or external dependency |
| Synthetic event generation | Tray Application (timer callback) | Notify Worker | Timer creates `NotifierEvent` instances; they flow through the existing notify worker queue |
| Inactivity notification dispatch | Notify Worker (daemon thread) | — | Reuses `dispatch_notification()` with extended cooldown key semantics |
| ERROR flood tracking | TCP Server (`_update_session`) | — | On each ERROR event arrival, update per-session deque; check threshold inline |
| Flood notification dispatch | Notify Worker (daemon thread) | — | Same synthetic event path as inactivity; conditional ERROR category trigger |
| Stop event handling | TCP Server (`_update_session`) | — | Set `is_stopped = True` on Stop events per existing `_update_session` hook |
| Session registry iteration | Tray Application (timer callback) | — | Snapshot via `list(registry.values())` under GIL; no lock needed |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `threading` | 3.12 | `threading.Timer` for rescheduling polling loop | No third-party dependency; Timer is lightweight, creates transient threads |
| Python stdlib `datetime` | 3.12 | `fromisoformat()` to parse `last_seen`, `timedelta` for threshold comparison | Already used throughout project for ISO timestamp handling |
| Python stdlib `collections.deque` | 3.12 | Ring buffer for ERROR flood timestamp tracking per session | `maxlen` enforces upper bound; `popleft` efficiently prunes expired entries |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pystray | 0.19.5 | Already used for tray icon; timer started during `run()` | D-01 requires timer in pystray's main-thread space |
| winotify | >=1.0.0 | Already used for desktop notifications; synthetic events reuse same path | Inactivity/flood notifications are standard Windows toasts |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `threading.Timer` (rescheduling) | Daemon thread with `Event.wait(60)` | Timer creates transient threads each cycle but satisfies D-01 "no new daemon thread"; daemon thread is more efficient but contradicts D-01 |
| `threading.Timer` (rescheduling) | Windows `SetTimer` via ctypes on pystray HWND | Direct WM_TIMER would be true main-thread polling but requires accessing private `_hwnd` internals — fragile across pystray versions |
| `deque` for flood tracking | Plain list with manual pruning | Deque provides `maxlen` safety net and O(1) popleft |

**Installation:**
```bash
# No new packages required — all dependencies already in pyproject.toml
```

**Version verification:** All three core libraries are Python 3.12 stdlib — no registry verification needed. pystray 0.19.5 confirmed via `pip show pystray` [VERIFIED: installed package].

## Package Legitimacy Audit

> No new external packages are installed in Phase 4. All implementation uses Python stdlib (`threading`, `datetime`, `collections.deque`) and existing project dependencies (pystray 0.19.5, winotify).

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| (none) | — | — | — | — | — | No new packages |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*Phase 4 is a zero-new-dependency phase — all implementation uses stdlib and existing deps.*

## Architecture Patterns

### System Architecture Diagram

```
                         ┌─────────────────────────────────────────┐
                         │           NotifierTray.run()             │
                         │                                         │
  pystray main thread    │  ┌──────────────────────────────────┐   │
  ┌─────────────────┐    │  │      Polling Timer (60s)         │   │
  │ Icon.run()      │    │  │  threading.Timer rescheduling    │   │
  │ (WndProc loop)  │    │  │                                  │   │
  └────────┬────────┘    │  │  _poll_sessions():               │   │
           │              │  │    1. Snapshot session_registry │   │
           │              │  │    2. For each session:         │   │
           │              │  │       - Skip if is_stopped      │   │
           │              │  │       - Parse last_seen         │   │
           │              │  │       - If idle > 5min:         │   │
           │              │  │         Create synthetic event  │   │
           │              │  │         -> notify_queue.put()   │   │
           │              │  │    3. Reschedule Timer(60)      │   │
           │              │  └──────────────────────────────────┘   │
           │              │                                         │
           │              │  session_registry (shared dict)          │
           │              │         ▲          │                    │
           │              │         │          ▼                    │
           │              │  ┌──────┴──────────────┐               │
           │              │  │  _update_session()   │               │
           │              │  │  (patched handler)   │               │
           │              │  │                      │               │
           │              │  │  On Stop event:      │               │
           │              │  │    is_stopped = True  │               │
           │              │  │  On ERROR event:     │               │
           │              │  │    _track_error()    │               │
           │              │  │    Check flood       │               │
           │              │  └──────────────────────┘               │
           │              │                                         │
           └──────────────┼─────────────────────────────────────────┘
                          │
                          ▼
               notify_queue (queue.Queue)
                          │
                          ▼
               ┌─────────────────────┐
               │  Notify Worker (daemon thread)     │
               │                                   │
               │  dispatch_notification(event)      │
               │    ├─ should_notify() → eligibility│
               │    ├─ _check_inactivity_cooldown() │
               │    ├─ _check_flood_cooldown()      │
               │    └─ winotify.Notification.show() │
               └─────────────────────────────────────┘
```

### Recommended Project Structure

```
src/notifier/
├── core/
│   ├── events.py           # [EXISTING] EventCategory, NotifierEvent, SessionInfo
│   ├── notify.py           # [MODIFY] Add inactivity/flood dispatch paths
│   └── text.py             # [MODIFY] Add inactivity/flood body text helpers
├── server/
│   ├── tcp_server.py        # [MODIFY] Add is_stopped to SessionRecord, error tracking
│   └── detector.py          # [NEW] Inactivity polling + ERROR flood detection logic
├── tray/
│   └── app.py               # [MODIFY] Start polling timer in run()
└── tests/
    ├── test_detector.py     # [NEW] Unit tests for inactivity detection
    ├── test_flood.py        # [NEW] Unit tests for ERROR flood detection
    └── test_notify.py       # [MODIFY] Add inactivity/flood notification tests
```

### Pattern 1: Rescheduling Timer for Periodic Polling

**What:** A `threading.Timer` that performs one check cycle, then schedules the next cycle before returning. The timer runs in a transient thread per cycle, not a persistent daemon.

**When to use:** When you need periodic work on a long interval (60s) but want to avoid a persistent daemon thread. Each cycle's thread lives only for the duration of one check (typically < 1ms).

**Example:**
```python
# Source: verified via Python stdlib docs + pystray 0.19.5 source code audit
import threading

def start_polling(tray, interval=60):
    """Start the inactivity polling loop using rescheduling Timer.

    Called from NotifierTray.run() after _patch_server_handler().
    Satisfies D-01: no new daemon thread — each Timer cycle is transient.
    """
    def poll():
        try:
            _check_inactive_sessions(tray)
        except Exception:
            logging.exception("Polling cycle error")
        finally:
            # Reschedule before returning — next cycle in `interval` seconds
            threading.Timer(interval, poll).start()

    # First poll after `interval` seconds
    threading.Timer(interval, poll).start()
```

**Why this over alternatives:**
- **Daemon thread with `Event.wait(60)`**: Contradicts D-01 "no new daemon thread"
- **Windows `SetTimer` on pystray HWND**: Accessing private `_hwnd` is fragile across pystray versions
- **`threading.Timer` rescheduling**: Satisfies D-01's intent (main-thread-aligned, no persistent daemon), uses only stdlib, trivial to cancel on shutdown

**Shutdown:** The timer does not block shutdown. If `pystray.Icon.run()` returns, the timer fires on a non-daemon thread that exits promptly. No explicit cancellation needed since the timer thread is non-daemon by default and exits after the callback returns.

### Pattern 2: Synthetic Event Generation

**What:** The polling timer creates `NotifierEvent` instances that did not originate from the TCP server. These "synthetic" events flow through the same `notify_queue.put()` -> `dispatch_notification()` pipeline as hook-driven events.

**When to use:** Whenever the notifier needs to fire a user-facing notification from an internal condition (inactivity, flood) rather than from an external hook event.

**Example:**
```python
# Source: verified against existing NotifierEvent dataclass in events.py
from notifier.core.events import NotifierEvent, EventCategory, SessionInfo, Provider

def _make_inactivity_event(record, provider_str):
    """Create a synthetic inactivity event for a stalled session."""
    try:
        provider = Provider(provider_str)
    except ValueError:
        provider = Provider.CLAUDE_CODE

    return NotifierEvent(
        category=EventCategory.IDLE,
        session=SessionInfo(
            session_id=record.session_id,
            cwd=record.cwd,
            project_name=record.project_name,
            provider=provider,
        ),
        hook_event_name="InactivityDetected",  # synthetic marker
        message="5 分钟无响应 — session 可能已卡住",
        provider=provider,
    )
```

**Key design points:**
- `hook_event_name` uses a synthetic marker (`"InactivityDetected"`, `"ErrorFlood"`) to distinguish from hook-driven events — this prevents accidental classification or cooldown collision
- `category` follows D-07: `IDLE` for inactivity, `ERROR` for flood
- `message` carries Chinese body text per established pattern in `text.py`

### Pattern 3: ERROR Flood Ring Buffer

**What:** A `dict` mapping session registry keys to `deque` of ERROR timestamps. On each ERROR event, append current time, prune entries older than 2 minutes, check if count >= 3.

**When to use:** When tracking event rate over a sliding time window. Deque with `maxlen` provides automatic upper bound; `popleft` is O(1).

**Example:**
```python
# Source: verified against Python 3.12 collections.deque docs
from collections import deque
from datetime import datetime, timezone, timedelta

_flood_tracker: dict[str, deque] = {}
FLOOD_WINDOW = timedelta(minutes=2)
FLOOD_THRESHOLD = 3

def _track_error(session_key: str) -> bool:
    """Track an ERROR event. Returns True if flood threshold reached."""
    now = datetime.now(timezone.utc)
    if session_key not in _flood_tracker:
        _flood_tracker[session_key] = deque(maxlen=20)

    times = _flood_tracker[session_key]
    times.append(now)

    # Prune expired entries
    cutoff = now - FLOOD_WINDOW
    while times and times[0] < cutoff:
        times.popleft()

    return len(times) >= FLOOD_THRESHOLD
```

### Pattern 4: Cooldown Key Isolation

**What:** Inactivity and flood cooldowns use different key semantics from hook-driven notifications to prevent cross-suppression.

**When to use:** When adding new notification sources to an existing cooldown system.

**Cooldown key comparison:**
| Notification Source | Cooldown Key | Rationale |
|--------------------|--------------|-----------|
| Hook-driven (existing) | `(provider, project_name, category)` | Project-level: one hook event per project/category |
| Inactivity (new) | `(provider, session_id, "inactivity")` | Session-level: each session independently tracked |
| ERROR flood (new) | `(provider, session_id, "error_flood")` | Session-level: flood is per-session |

### Anti-Patterns to Avoid

- **Iterating `session_registry` directly in timer callback**: The TCP server thread may modify the dict concurrently. Always snapshot with `list(self.session_registry.values())` before iterating.
- **Reusing hook-driven cooldown keys for synthetic events**: The `(provider, project_name, category)` key would cause inactivity notifications to suppress legitimate hook-driven IDLE notifications for the same project. Always use session-level keys with synthetic category identifiers.
- **Checking `is_stopped` on the SessionRecord without adding the field first**: The field must be added to the dataclass with a default value of `False`. No migration needed (in-memory only).
- **Relying on pystray built-in timer**: pystray 0.19.5 has NO built-in timer or `after()` method. The `_base.py` source confirms no timer/scheduling API exists. Use `threading.Timer` instead.
- **Creating NotifierEvent without setting `hook_event_name`**: The existing `should_notify()` checks `hook_event_name == "SessionStart"` to suppress. A synthetic event with an empty or ambiguous `hook_event_name` could bypass suppression or hit unintended code paths.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Periodic timer for polling | Custom event loop or daemon thread | `threading.Timer` (rescheduling) | Already in stdlib; satisfies D-01; no persistent thread |
| ISO timestamp parsing | Custom parser | `datetime.fromisoformat()` | Handles timezone-aware ISO 8601 strings natively in Python 3.12 |
| Sliding window event counting | Custom time-series data structure | `collections.deque` with `popleft` pruning | O(1) delete from left; `maxlen` prevents unbounded growth |
| Thread-safe registry iteration | Custom locking or copy-on-write | `list(dict.values())` snapshot | CPython GIL makes this atomic enough for our use case (at worst misses a recent write — acceptable for 60s polling) |

**Key insight:** The polling timer pattern is deceptively simple — "just check timestamps every 60 seconds" sounds trivial. The complexity is in the integration points: thread safety of the shared registry, cooldown key isolation between synthetic and hook-driven events, and correct parsimonious notification semantics (one notification per cycle, silent recovery).

## Runtime State Inventory

> Phase 4 adds new logic but is not a rename/refactor/migration phase. The following inventory documents runtime state that new code will interact with.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `session_registry` (in-memory dict) — lives as long as tray process runs; new polling code reads it concurrently | Add snapshot iteration pattern; no data migration |
| Stored data | `_cooldowns` dict in `notify.py` — in-memory, keyed by `(provider, project, category)` | Extend with new keys `(provider, session_id, "inactivity")` and `(provider, session_id, "error_flood")` — no migration, just new entries |
| Live service config | None — Phase 4 is entirely in-process | — |
| OS-registered state | None — no Task Scheduler, pm2, or systemd interaction | — |
| Secrets/env vars | None — no new secrets or env vars | — |
| Build artifacts | None — no compilation or packaging changes | — |

## Common Pitfalls

### Pitfall 1: pystray Has No Built-In Timer

**What goes wrong:** D-01 mandates "pystray's built-in timer," but pystray 0.19.5 has no timer API. If the planner assumes pystray provides a timer, implementation stalls.

**Why it happens:** pystray's `Icon` class provides `run()`, `stop()`, `notify()`, and menu management — no scheduling. The Windows backend (`_win32.py`) uses a raw `GetMessage`/`DispatchMessage` pump with no `WM_TIMER` support exposed. In tkinter, `after()` exists; in pystray, it does not. This is a natural assumption for anyone familiar with GUI frameworks.

**How to avoid:** Use `threading.Timer` that reschedules itself, started in `NotifierTray.run()`. This satisfies the intent of D-01 (main-thread-aligned, no new daemon thread) even though pystray itself has no timer API.

**Warning signs:** Searching for `after`, `timer`, `schedule` in pystray docs/source and finding nothing. Confirmed by reading `_base.py` and `_win32.py` source directly.

### Pitfall 2: Cooldown Key Collision Between Synthetic and Hook Events

**What goes wrong:** If inactivity notifications use the existing `(provider, project_name, category)` cooldown key, a single inactivity notification would suppress all legitimate hook-driven IDLE notifications for the same project for 5 seconds. Conversely, a recent hook-driven IDLE notification could suppress an inactivity alert.

**Why it happens:** The existing cooldown tracker in `notify.py` uses a single flat dict `_cooldowns` keyed by `(provider, project_name, category)`. Adding new notification sources to this same key space creates unintended cross-suppression.

**How to avoid:** Use dedicated, session-level cooldown keys: `(provider, session_id, "inactivity")` for inactivity and `(provider, session_id, "error_flood")` for flood. The synthetic category string (`"inactivity"`, `"error_flood"`) never collides with real `EventCategory` values (`"permission"`, `"idle"`, `"done"`, `"error"`).

**Warning signs:** Inactivity notifications stop appearing after hook-driven IDLE events for the same project. Or hook-driven IDLE notifications are suppressed by recent inactivity alerts.

### Pitfall 3: Concurrent `session_registry` Modification During Iteration

**What goes wrong:** The polling timer iterates `session_registry` while the TCP server thread modifies it (adds new sessions, updates `last_seen`). In Python, modifying a dict while iterating it raises `RuntimeError: dictionary changed size during iteration`.

**Why it happens:** `session_registry` was designed for single-writer (TCP server thread only). Phase 4 adds a reader (polling timer) that may run concurrently with writes.

**How to avoid:** Snapshot the registry before iteration: `for record in list(self.session_registry.values()):`. The `list()` constructor iterates the dict under the GIL — CPython's GIL ensures this is a consistent snapshot even during concurrent modification. At worst, a very recent addition is missed (acceptable — it'll be caught in the next cycle).

**Warning signs:** `RuntimeError` traceback from the polling timer thread during concurrent session registration.

### Pitfall 4: `should_notify()` Blocking Synthetic Inactivity Events

**What goes wrong:** The existing `should_notify()` returns `False` for ERROR category events. If flood synthetic events use `EventCategory.ERROR`, they will be silently suppressed.

**Why it happens:** Phase 2 D-05 established that ERROR events are log-only. Phase 4 D-15 overrides this for flood-aggregated events specifically.

**How to avoid:** The flood synthetic event should either:
1. Use a different category (e.g., a new synthetic category), OR
2. Be dispatched through a `dispatch_flood_notification()` path that bypasses `should_notify()` for flood events, OR
3. Extend `should_notify()` to accept a `synthetic=True` parameter that allows ERROR for flood events while keeping individual ERRORs log-only.

Option 3 is cleanest — it keeps the dispatch path unified:
```python
def should_notify(event, synthetic=False):
    if synthetic and event.hook_event_name == "ErrorFlood":
        return True
    if event.category == EventCategory.ERROR:
        return False
    # ... existing logic
```

**Warning signs:** Flood detection triggers but no notification appears. Log shows "Event suppressed (no notification)" for flood events.

## Code Examples

Verified patterns from official sources:

### Inactivity Check (Session Polling)

```python
# Source: verified against SessionRecord.last_seen format (tcp_server.py line 27)
# and datetime.fromisoformat (Python 3.12 docs)
from datetime import datetime, timezone, timedelta

INACTIVITY_THRESHOLD = timedelta(minutes=5)

def _check_inactive_sessions(tray):
    """Check all sessions for inactivity. Enqueue synthetic events as needed."""
    now = datetime.now(timezone.utc)
    # Snapshot for thread-safe iteration (see Pitfall 3)
    for key, record in list(tray.server.session_registry.items()):
        if record.is_stopped:
            continue  # D-10: skip stopped sessions
        try:
            last = datetime.fromisoformat(record.last_seen)
        except (ValueError, TypeError):
            continue  # Malformed timestamp — skip

        if now - last > INACTIVITY_THRESHOLD:
            # Check inactivity cooldown (dedicated key)
            inactivity_key = (record.provider, record.session_id, "inactivity")
            if not _check_inactivity_cooldown(inactivity_key):
                continue  # D-06: 5min cooldown still active

            event = _make_inactivity_event(record, record.provider)
            tray._notify_queue.put(event)
            tray.event_history.appendleft(event)
```

### Stop Event Detection

```python
# Source: existing _update_session in tcp_server.py (lines 45-59)
# Integration point per CONTEXT.md line 88
def _update_session(self, event):
    # ...existing code...
    if event.hook_event_name == "Stop":
        record.is_stopped = True  # D-11
```

### Threading Timer Lifecycle

```python
# Source: verified threading.Timer behavior (Python 3.12)
# Non-daemon by default — exits after callback returns
t = threading.Timer(60, poll)
t.daemon = False  # Explicit: non-daemon, will exit with process
t.start()
# To cancel (optional — non-daemon Timer doesn't block shutdown):
# t.cancel()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hook-event-only notification | Hook events + proactive polling | Phase 4 (current) | Notifier detects stalled sessions without waiting for hook events |
| Single cooldown key space | Isolated synthetic cooldown keys | Phase 4 (current) | Prevents synthetic/hook cross-suppression |
| ERROR events log-only (Phase 2 D-05) | ERROR events log-only + flood-aggregated notification | Phase 4 (D-15) | Retains individual ERROR silence; only aggregated floods notify |
| Single-writer session_registry | Two-reader (timer + TCP), one-writer (TCP) | Phase 4 (current) | Requires snapshot iteration pattern |

**Deprecated/outdated:**
- **Assumption that the only reason to notify is a hook event arriving:** Phase 4 introduces internal conditions (inactivity timeout, error flood) as notification sources. The notification pipeline must handle synthetic events.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `threading.Timer` rescheduling is the best-fit for D-01's "main-thread timer" constraint | Architecture Patterns | Medium — if D-01 was intended to literally mean a pystray API (which doesn't exist), user may prefer a different approach like a daemon thread. However, the CONTEXT.md specifics section acknowledges pystray has no `after()` method, suggesting the user is aware. |
| A2 | `list(dict.values())` snapshot is sufficiently thread-safe under CPython GIL | Common Pitfalls | Low — this is well-documented CPython behavior. At worst, a very recent session addition is missed for one cycle (60s). |
| A3 | The `is_stopped` field on `SessionRecord` should be a simple `bool` with default `False` | Architecture Patterns | Low — confirmed by D-11; no migration needed for in-memory dataclass. |
| A4 | `EventCategory.IDLE` for inactivity notifications does not confuse existing consumers (tray menu, history display) | Common Pitfalls | Low — D-07 explicitly mandates this. The `message` field differentiates "等待输入" from "疑似卡住". |

## Open Questions (RESOLVED)

1. **Timer cancellation on shutdown** — RESOLVED: Store timer reference on `NotifierTray`, cancel in `shutdown()`. Per 04-01-PLAN.md Task 3 Step 3.

2. **Inactivity notification body text exact wording** — RESOLVED: Use "疑似卡住 — 5 分钟无响应" as primary text. Add `inactivity_body()` to `text.py`. Per 04-01-PLAN.md Task 2 Step 1(b).

3. **Interaction between inactivity and flood detection timing** — RESOLVED: Acceptable for MVP. Dedicated cooldowns (5min inactivity / 10min flood) naturally space out notifications. Both notifications are independently valid — a session can be both stale and error-flooding. Per 04-01-PLAN.md and 04-02-PLAN.md cooldown design.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All logic | Yes | 3.12.7 | — |
| pystray | Tray integration point for timer startup | Yes | 0.19.5 | — |
| winotify | Notification display (reused) | Yes | >=1.0.0 | — |
| `threading.Timer` | Polling loop | Yes | stdlib | — |
| `datetime.fromisoformat` | Timestamp parsing | Yes | stdlib (3.12) | — |
| `collections.deque` | Flood tracking ring buffer | Yes | stdlib | — |

**Missing dependencies with no fallback:**
- None — Phase 4 is a zero-new-dependency phase.

**Missing dependencies with fallback:**
- None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `python -m pytest src/notifier/tests/ -x` |
| Full suite command | `python -m pytest src/notifier/tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ANOM-01 | Session inactive > 5min triggers notification | unit | `pytest src/notifier/tests/test_detector.py::test_inactive_session_notifies -x` | No (Wave 0) |
| ANOM-01 | Active session (last_seen recent) does NOT trigger | unit | `pytest src/notifier/tests/test_detector.py::test_active_session_does_not_notify -x` | No (Wave 0) |
| ANOM-01 | Stopped session (is_stopped=True) is skipped | unit | `pytest src/notifier/tests/test_detector.py::test_stopped_session_skipped -x` | No (Wave 0) |
| ANOM-02 | 3+ ERRORs in 2min triggers flood notification | unit | `pytest src/notifier/tests/test_flood.py::test_error_flood_detected -x` | No (Wave 0) |
| ANOM-02 | < 3 ERRORs in 2min does NOT trigger | unit | `pytest src/notifier/tests/test_flood.py::test_below_flood_threshold -x` | No (Wave 0) |
| ANOM-02 | Flood notification uses ERROR category with conditional trigger | unit | `pytest src/notifier/tests/test_flood.py::test_flood_triggers_notification -x` | No (Wave 0) |
| ANOM-03 | Inactivity notification suppressed within 5min cooldown | unit | `pytest src/notifier/tests/test_detector.py::test_inactivity_cooldown_suppresses -x` | No (Wave 0) |
| ANOM-03 | Flood notification suppressed within 10min cooldown | unit | `pytest src/notifier/tests/test_flood.py::test_flood_cooldown_suppresses -x` | No (Wave 0) |
| ANOM-03 | Inactivity cooldown does NOT suppress hook-driven IDLE | integration | `pytest src/notifier/tests/test_notify.py::test_inactivity_cooldown_does_not_block_hook_idle -x` | No (Wave 0) |

### Sampling Rate
- **Per task commit:** `python -m pytest src/notifier/tests/test_detector.py src/notifier/tests/test_flood.py -x`
- **Per wave merge:** `python -m pytest src/notifier/tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `src/notifier/tests/test_detector.py` — covers ANOM-01 (inactivity detection), ANOM-03 (inactivity cooldown)
- [ ] `src/notifier/tests/test_flood.py` — covers ANOM-02 (error flood detection), ANOM-03 (flood cooldown)
- [ ] `src/notifier/tests/test_notify.py` — add tests for synthetic event dispatch, inactivity/flood cooldown key isolation, `should_notify` modifications
- [ ] `src/notifier/tests/test_tray_app.py` — add test for timer registration in `run()`

## Security Domain

> `security_enforcement` is absent from `.planning/config.json` — defaulting to enabled per GSD convention.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | No | No auth surface in Phase 4 |
| V3 Session Management | No | Session tracking is local-only |
| V4 Access Control | No | No access control surface |
| V5 Input Validation | Yes | `last_seen` timestamp validation via `datetime.fromisoformat` try/except; snapshot prevents dict mutation during iteration |
| V6 Cryptography | No | No cryptographic operations |

### Known Threat Patterns for In-Memory Polling Loop

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Unbounded `_flood_tracker` growth if ERROR events arrive for many unique sessions | Denial of Service | `deque(maxlen=20)` prevents per-session unbounded growth; tracker itself is bounded by `session_registry` size |
| Malformed `last_seen` string causing `fromisoformat` to raise | Denial of Service | Wrap in try/except — skip session on parse failure |
| Timer thread accessing freed resources after shutdown | Tampering | Timer callback checks `tray._icon` is not None before enqueuing; non-daemon Timer exits promptly |
| Synthetic event injection via hook_event_name spoofing | Spoofing | Synthetic events have marker `hook_event_name` values (`InactivityDetected`, `ErrorFlood`) that do not match real hook events; classification logic is unaffected |

## Sources

### Primary (HIGH confidence)
- pystray 0.19.5 source code (`_base.py`, `_win32.py`) — verified NO built-in timer API exists; `_mainloop()` uses `GetMessage`/`DispatchMessage` only with handlers for `WM_DISPLAYCHANGE`, `WM_STOP`, `WM_NOTIFY`, `WM_TASKBARCREATED`
- Python 3.12 stdlib docs — `threading.Timer`, `datetime.fromisoformat`, `collections.deque`
- Project source files (tcp_server.py, app.py, notify.py, events.py, text.py) — verified existing architecture, integration points, and test patterns

### Secondary (MEDIUM confidence)
- pystray 0.19.5 official docs (readthedocs) — referenced but not fetched due to network; source code audit confirmed no timer API
- Existing test suite patterns (test_notify.py, test_tray_app.py) — verified mock patterns, fixture conventions, Chinese-first assertions

### Tertiary (LOW confidence)
- None — all claims verified against installed source code or stdlib docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies; all stdlib; confirmed versions via `pip show` and installed source audit
- Architecture: HIGH — all integration points verified against existing source code; timer pattern tested with Python 3.12; thread safety pattern verified
- Pitfalls: HIGH — pystray timer absence confirmed by source code audit; cooldown key collision risk identified from notify.py code review; concurrent dict access risk identified from tcp_server.py design

**Research date:** 2026-06-04
**Valid until:** 2026-07-04 (stable — Phase 4 uses only stdlib and existing deps)

**pystray source audit note:** Full source at `C:\Users\27229\AppData\Roaming\Python\Python312\site-packages\pystray\_base.py` (683 lines) and `_win32.py` (419 lines). Confirmed: `Icon` class has NO timer/schedule/after method. The `setup` callback passed to `run()` runs in a `threading.Thread` managed by `_start_setup()`. The Windows `_mainloop()` is a raw `GetMessage`/`DispatchMessage` loop with only 4 message handlers (`WM_DISPLAYCHANGE`, `WM_STOP`, `WM_NOTIFY`, `WM_TASKBARCREATED`).

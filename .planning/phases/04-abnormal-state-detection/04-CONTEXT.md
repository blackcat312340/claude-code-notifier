# Phase 4: Abnormal-State Detection - Context

**Gathered:** 2026-06-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend the notifier beyond direct hook notifications by detecting stalled or abnormal Claude/Codex sessions. Add a proactive inactivity detection loop, inactivity-triggered desktop notifications with dedicated cooldown, session lifecycle state tracking, and at least one non-inactivity abnormal-state notification path (ERROR flood detection).

**In scope:** Inactivity detection via polling timer (60s interval, 5min threshold), inactivity notifications (IDLE category, single-shot with 5min cooldown, silent recovery), SessionRecord stop-state tracking, ERROR flood detection (3 errors / 2min, 10min cooldown).

**Out of scope:** Heartbeat protocol, persistent session storage, session registry cleanup/expiry, TCP connection state tracking, notification click actions, remote delivery, configurable thresholds (v1 hardcoded with config points reserved).
</domain>

<decisions>
## Implementation Decisions

### Inactivity Detection
- **D-01:** Polling loop — **pystray main-thread timer**. Use pystray's built-in timer/callback on the main thread. No new daemon thread. Event-driven-only is insufficient — it fails when no events arrive, which is exactly the scenario we need to detect.
- **D-02:** Polling interval — **60 seconds**. Balances detection latency (max 1min beyond the 5min threshold) and resource consumption.
- **D-03:** Inactivity threshold — **uniform 5 minutes**. All sessions, all providers share the same threshold. Directly satisfies ANOM-01. Reserve config points for future customization but hardcode for v1.
- **D-04:** Heartbeat — **not needed**. Existing hook events (Notification, Stop, PermissionRequest, SessionStart) update `last_seen` on arrival. No additional heartbeat protocol from hook CLI to TCP server.

### Inactivity Notification Rules
- **D-05:** Notification frequency — **single notification per inactivity cycle**. Fire once when a session exceeds the 5min threshold. Timer resets when a new event arrives for that session. No repeated reminders.
- **D-06:** Inactivity cooldown — **5 minutes, dedicated**. Separate from the existing 5s general notification cooldown in `notify.py`. Keyed by `(provider, session_id, "inactivity")` to avoid cross-talk with hook-driven notifications.
- **D-07:** Notification category — **reuse IDLE**. Inactivity notifications use the existing `EventCategory.IDLE`. The notification body text differentiates "等待输入" (explicit idle_prompt) from "疑似卡住" (inactivity detected) via message content, not category.
- **D-08:** Recovery — **silent**. When an inactive session receives a new event, reset the inactivity timer silently. No "recovered" notification.

### Active Session Definition
- **D-09:** Monitoring scope — **all registered sessions**. Every session in `session_registry` is checked for inactivity, regardless of lifecycle stage.
- **D-10:** Stop handling — **skip stopped sessions, do not remove**. Sessions that received a Stop event are excluded from inactivity checks via a status flag. Sessions are never automatically removed from the registry in v1.
- **D-11:** SessionRecord extension — **add `is_stopped` boolean field**. Default `False`, set to `True` on Stop event. Inactivity polling loop checks `if not record.is_stopped and inactive(record) → notify`.
- **D-12:** Activity signal — **`last_seen` only**. No event counting, no TCP connection state tracking. Any event arriving for a session updates `last_seen` and constitutes proof of activity.

### Abnormal State Path (Non-Inactivity)
- **D-13:** v1 abnormal path — **ERROR flood detection**. When a single session generates 3 or more ERROR events within a 2-minute window, emit a user-facing notification. This catches hook misconfiguration and malformed payload patterns.
- **D-14:** Flood threshold — **3 ERROR events / 2 minutes** per session. Sensitive enough to catch configuration errors quickly without excessive false positives.
- **D-15:** Flood notification category — **ERROR with conditional trigger**. The ERROR category is added to notification eligibility, but only the flood-aggregated event fires a notification — individual ERROR events remain log-only (preserving Phase 2 D-05 intent).
- **D-16:** Flood cooldown — **10 minutes per session**. Longer than inactivity cooldown because flood-inducing problems (e.g., hook misconfiguration) are unlikely to be fixed within seconds.

### Claude's Discretion
No areas were deferred to Claude — all decisions were explicitly captured during discussion.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project-Level
- `.planning/PROJECT.md` — Scope, Windows-first constraint, all-local-project monitoring, notifier-only product role
- `.planning/REQUIREMENTS.md` — Phase 4 requirements: ANOM-01 (5min inactivity detection), ANOM-02 (error-like abnormal state reminder), ANOM-03 (duplicate suppression with cooldown)
- `.planning/ROADMAP.md` — Phase 4 success criteria: (1) heartbeat/last_seen tracking for 5min detection, (2) inactivity deduplication, (3) at least one error-like abnormal path

### Prior Phase Artifacts
- `.planning/phases/01-hook-event-backbone/01-CONTEXT.md` — Event taxonomy (D-01: 4 categories), session identity composite key, IPC bridge design
- `.planning/phases/02-first-useful-reminders/02-CONTEXT.md` — D-05 (PERMISSION/IDLE/DONE notify, ERROR log-only), D-06 (30s cooldown per project/category), notification format, tray/notification process architecture
- `.planning/phases/03-operator-trust-surface/03-CONTEXT.md` — Event history ring buffer (deque maxlen=50), tray menu structure, event detail popup
- `.planning/phases/03.1-codex-hook-support-chinese-localization/03.1-CONTEXT.md` — D-05 (4 stable categories), D-09 (unified inactivity detection for both providers in Phase 4), provider-aware session key, Chinese-first UI copy

### Phase 4 Key Source Files
- `src/notifier/server/tcp_server.py` — `SessionRecord` (has `last_seen`, comment says "lifecycle management deferred to Phase 4"), `NotifierServer.session_registry`, `_update_session()`
- `src/notifier/tray/app.py` — `NotifierTray` main process, `_patch_server_handler()`, `_notify_queue`, `event_history` deque, pystray main thread
- `src/notifier/core/notify.py` — `dispatch_notification()`, `NOTIFY_COOLDOWN_S` (5s), `NOTIFY_CATEGORIES` set, cooldown tracker
- `src/notifier/core/events.py` — `EventCategory` enum (PERMISSION, IDLE, DONE, ERROR), `NotifierEvent` dataclass, `SessionInfo`, `Provider`
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`SessionRecord.last_seen`** — Already tracked as ISO timestamp string. Inactivity detection reads this directly. No schema change needed — only the polling loop is new.
- **`NotifierTray._patch_server_handler()`** — Existing pattern for intercepting events post-session-update. The inactivity polling timer can be registered here or in `run()`. Same pattern as how notifications were bolted on in Phase 2.
- **`dispatch_notification()`** — Existing notification dispatch with cooldown logic. Inactivity and flood notifications can either extend this function or add a parallel dispatch path. The `_check_cooldown` key pattern `(provider, project_name, category)` is extensible.
- **`NotifierTray.event_history`** — Existing deque. Inactivity and flood events should be appended here for tray menu visibility, same as hook-driven events.
- **`notify.py` cooldown tracker** — In-memory dict pattern. Inactivity and flood cooldowns can follow the same structure with different key semantics.

### Established Patterns
- **Hook-driven architecture** — TCP server receives events, updates session, enqueues to notify queue. Phase 4 adds a second event source: the polling timer creates "synthetic" inactivity events that flow through the same notification pipeline.
- **Chinese-first copy** — All user-visible text uses `text.py` helpers. Inactivity and flood notification bodies follow the same pattern.
- **In-memory only** — No persistence. Sessions, history, cooldowns all live in memory. Inactivity detection operates on the live `session_registry` dict.
- **Daemon thread architecture** — TCP server and notify worker are daemon threads. The polling timer lives on the main thread via pystray, not as a new thread.

### Integration Points
- **`NotifierTray.run()`** — Where the pystray timer should be registered. After `_patch_server_handler()` and before `self._icon.run()`.
- **`NotifierServer._update_session()`** — Stop event detection: when `hook_event_name == "Stop"`, set `record.is_stopped = True`. This is the trigger for D-11.
- **`dispatch_notification()` / `should_notify()`** — Needs awareness of inactivity (D-07: IDLE category, synthetically generated) and flood (D-15: ERROR conditional trigger). Synthetic events from the polling loop need to pass through the same notification path.
- **SessionRecord dataclass** — Add `is_stopped: bool = False` field. No migration needed — in-memory only.
</code_context>

<specifics>
## Specific Ideas

- Inactivity notification body examples (Chinese): "5 分钟无响应 — session 可能已卡住", "session 无响应 — 请检查终端状态"
- ERROR flood notification body example: "检测到异常 — 2 分钟内收到 3 条错误事件，hook 配置可能有问题"
- pystray timer implementation: pystray does not have a built-in `after()` method like tkinter. The polling loop can use `threading.Timer` scheduled from the main thread, or a simple `while` loop with `time.sleep(60)` in the patched handler if pystray's event loop permits.
- Inactivity cooldown key: `(provider, session_id, "inactivity")` — session-level, not project-level. Different from the existing `(provider, project_name, category)` key which is project-level.
- Flood tracking: a small in-memory ring per session `{(session_key): deque of ERROR timestamps}`. On each ERROR event, append timestamp, prune entries older than 2 minutes, check if count >= 3.
- Stop detection: check `event.hook_event_name == "Stop"` in `_update_session()` to set `is_stopped = True`. Both Claude Code and Codex emit Stop events.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 4 scope.
</deferred>

---

*Phase: 4-Abnormal-State Detection*
*Context gathered: 2026-06-04*

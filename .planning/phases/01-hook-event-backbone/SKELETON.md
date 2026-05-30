# Walking Skeleton -- Claude Code Notifier

**Phase:** 1
**Generated:** 2026-05-30

## Capability Proven End-to-End

A developer can run the notifier TCP server, pipe a simulated Claude Code hook event (JSON on stdin) to the hook CLI, and observe the event arrive in the server's session registry with correct classification (permission/idle/done/error) and project metadata (session_id, project name from cwd).

## Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Runtime | Python 3.12.7 | Available on target machine; stdlib covers all Phase 1 needs |
| CLI Framework | Typer 0.25.0 | Already installed; type-safe, auto-help, lightweight; ideal for hook and config CLIs |
| Deep-merge Library | mergedeep 1.3.4 | Handles recursive dict merging with ADDITIVE strategy; more robust than a custom recursive merge for edge cases (list merge, type safety) |
| IPC Mechanism | TCP localhost (127.0.0.1:47921) | Cross-platform; works identically on Windows/Linux/macOS; no platform-specific APIs like named pipes |
| Wire Format | NDJSON (newline-delimited JSON) | Simple, parseable line-by-line; human-readable for debugging; matches the one-event-per-invocation pattern of hook CLIs |
| Event Schema | Dataclass-based NotifierEvent with EventCategory enum | Type-safe, serializable via asdict(), easily extended with new event types in later phases |
| Project Name | Leaf directory from cwd | Zero-config; works for any directory without git/config files; matches D-04 |
| Session Key | (session_id, cwd) composite | Enables project grouping; handles edge cases like fresh sessions with same ID; matches D-05 |
| Settings Integration | Deep-merge only the `hooks` key in Claude Code settings.json | Preserves all unrelated user settings (themes, custom commands, other hooks); matches D-07 |
| Ownership Tracking | Separate notifier config file (~/.claude/.notifier-ownership.json) | No metadata keys injected into Claude Code settings entries; matches D-09 |
| Packaging | pyproject.toml with [project.scripts] | Modern Python standard (PEP 621); creates CLI entry points on PATH |
| Test Framework | pytest 9.0.3 | Already installed; fixtures, parametrize, asyncio support for TCP server tests |

## Stack Touched in Phase 1

- [x] Project scaffold (pyproject.toml, package structure, CLI entry points)
- [x] Event pipeline -- stdin JSON -> classify -> TCP send -> server receive
- [x] Session registry -- in-memory dict keyed by (session_id, cwd) composite
- [x] Session lifecycle -- records created on SessionStart with last-seen timestamp, no expiry (Phase 4)
- [x] Hook config generation -- HOOK_ENTRIES dict with 4 entries (Notification x2 matchers, SessionStart, Stop)
- [x] Settings deep-merge -- read existing settings.json -> merge hooks key -> write back
- [x] Config CLI -- notifier-config install command
- [x] Ownership tracking -- separate config file for tracking which hooks the notifier owns
- [x] Test suite -- pytest with unit tests for classification, session, IPC, and integration tests for CLI
- [x] Documented run command -- `python -m notifier` starts the TCP server; `echo '{...}' | notifier-hook Notification` sends an event

## Out of Scope (Deferred to Later Slices)

- Desktop notifications (Phase 2 - ATTN-01/02/03)
- Tray application (Phase 2 - TRAY-01)
- Event history persistence to disk (Phase 3 - SESS-03)
- Session expiry and cleanup (Phase 4 - deferred per D-06)
- Anomaly/inactivity detection (Phase 4 - ANOM-01/02/03)
- Hook uninstall (Phase 5 - HOOK-02)
- Named pipes or Unix sockets (TCP is cross-platform and sufficient)
- Per-project opt-in/opt-out (all-projects monitoring per constraint)
- Click-action notifications (not required in v1 per constraint)

## Subsequent Slice Plan

- Phase 2: First Useful Reminders -- Windows desktop notifications for permission and idle events, tray background process
- Phase 3: Operator Trust Surface -- recent event history, tray inspection view, session navigation
- Phase 4: Abnormal-State Detection -- stalled session detection, inactivity reminders with cooldown
- Phase 5: Safe Hook Lifecycle -- uninstall command, status reporting, idempotent lifecycle management

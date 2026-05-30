# Phase 1: Hook Event Backbone - Context

**Gathered:** 2026-05-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish the event pipeline backbone: a Python CLI entrypoint that receives Claude Code hook events on stdin, normalizes them into notifier events (4 categories), identifies sessions and projects from hook payloads, and can be installed into user-level Claude settings via deep-merge. The hook CLI must stay lightweight — all heavy processing is deferred to the resident notifier process (Phase 2+).

**In scope:** Hook event ingestion, event normalization/categorization, session/project identification, hook config generation and installation into settings.json.

**Out of scope:** Desktop notifications (Phase 2), tray UI (Phase 2), event history storage (Phase 3), anomaly detection (Phase 4), hook uninstall (Phase 5).
</domain>

<decisions>
## Implementation Decisions

### Event Taxonomy
- **D-01:** 4 notifier event categories: `permission`, `idle`, `done`, `error`
- **D-02:** Register 4 Claude Code hook event types: Notification, Stop, Idle, SessionStart
- **D-03:** Classify Notification events by inspecting the hook's `type` field (values: `permission`, `error`, `info`). `error` category also fires on hook process failures (non-zero exit, timeout).

### Project & Session Identity
- **D-04:** Project display name = leaf directory name from `cwd` in the hook payload (e.g., `D:\code\my-project` → `my-project`). No config file or git parsing in v1.
- **D-05:** Session identity = `(session_id, cwd)` composite key — enables project grouping and handles edge cases.
- **D-06:** Session lifecycle management (expiry, cleanup) deferred to Phase 4. Phase 1 creates session records on SessionStart with a last-seen timestamp but does not expire them.

### Hook Configuration Strategy
- **D-07:** Deep-merge into the `hooks` key only when writing to `~/.claude/settings.json`. All other user settings are preserved untouched.
- **D-08:** One hook config entry per event type (4 entries total), each pointing to the same notifier CLI with the event type as an argument.
- **D-09:** Hook ownership tracked via a separate notifier config file — not by adding metadata keys to the Claude Code settings.json hook entries.

### IPC Bridge
- **D-10:** Hook CLI communicates with the resident notifier over a local TCP socket (localhost). The notifier listens; the CLI connects, sends, disconnects.
- **D-11:** On connection failure: retry with exponential backoff (~3 attempts over ~5 seconds), then log and drop the event. Hook CLI returns quickly — Claude Code is not blocked.
- **D-12:** Wire format: newline-delimited JSON (NDJSON). Each event is one JSON line terminated by `\n`.

### Claude's Discretion
No areas were deferred to Claude — all decisions were explicitly captured.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project-Level
- `.planning/PROJECT.md` — Scope, constraints (Windows-first, hooks-only, all-projects monitoring), key decisions, and out-of-scope items
- `.planning/REQUIREMENTS.md` — Phase 1 requirements: HOOK-01 (install hooks without destroying config), HOOK-03 (receive and forward hook payloads), SESS-01 (track sessions across projects), SESS-02 (derive project display name)
- `.planning/ROADMAP.md` — Phase 1 success criteria: (1) hook config generation/installation, (2) hook events reach notifier entrypoint with normalized metadata, (3) multi-session distinguishability

### Research
- `.planning/research/SUMMARY.md` — Stack decision (Python), watch-outs (hook latency, destructive settings edits, noisy heuristics), and product implication (hook-to-event pipeline as MVP foundation)

### External
- Claude Code hooks documentation: `https://docs.anthropic.com/en/docs/claude-code/hooks` — Official hook event types, JSON stdin format, settings.json structure, and session metadata fields
</canonical_refs>

<code_context>
## Existing Code Insights

Greenfield project — no existing codebase.

### Established Patterns
- Python stack (from research) — use idiomatic Python project structure
- Windows-first — use Windows-native APIs where beneficial (notifications, tray), but keep IPC and event processing cross-platform-ready

### Integration Points
- `~/.claude/settings.json` — hook entries are written here (deep-merge, hooks key only)
- Claude Code hook stdin — hook CLI receives JSON payloads with `session_id`, `cwd`, `transcript_path`, and event-specific fields
- Local TCP port — the notifier listens; the CLI connects per-event
</code_context>

<specifics>
## Specific Ideas

No specific references or "I want it like X" moments from discussion — open to standard approaches.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 1 scope.
</deferred>

---

*Phase: 1-Hook Event Backbone*
*Context gathered: 2026-05-30*

# Phase 1: Hook Event Backbone - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-30
**Phase:** 01-Hook Event Backbone
**Areas discussed:** Event taxonomy, Project identity, Hook merge strategy, IPC bridge

---

## Event Taxonomy

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal: attention + done | Two categories only, defers nuance to later phases | |
| 3-category: attention, done, info | Adds info for lifecycle events | |
| 4-category: permission, idle, done, error | Splits attention into permission and idle, adds error | ✓ |

**User's choice:** 4-category: permission, idle, done, error
**Notes:** Maps directly to requirements (ATTN-01→permission, ATTN-02→idle, ANOM-02→error).

---

| Option | Description | Selected |
|--------|-------------|----------|
| Notification + Stop + SessionStart | Minimal set covering core requirements | |
| Notification + Stop + Idle + SessionStart | Adds Idle for ATTN-02 idle-waiting | ✓ |
| All 7 hook events | Rich data for later phases | |

**User's choice:** Notification + Stop + Idle + SessionStart
**Notes:** Covers all v1 attention signals. SessionEnd, PreToolUse, PostToolUse excluded for now.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Inspect Notification type field | Read type field: permission/error/info | ✓ |
| Keyword matching on text | Parse notification message for keywords | |
| All Notifications→permission | Only hook failures produce error events | |

**User's choice:** Inspect Notification type field
**Notes:** Deterministic classification. Error category also from hook process failures (non-zero exit, timeout).

---

## Project Identity

| Option | Description | Selected |
|--------|-------------|----------|
| Leaf directory name from cwd | Simplest, zero-config | ✓ |
| Leaf + optional config override | Default + .notifier.toml for custom names | |
| git remote-based naming | Parse git remote for user/repo format | |

**User's choice:** Leaf directory name from cwd
**Notes:** Works automatically across all projects, no setup required.

---

| Option | Description | Selected |
|--------|-------------|----------|
| session_id alone | UUID is globally unique | |
| (session_id, cwd) composite key | Enables project grouping, handles edge cases | ✓ |
| session_id as key, cwd as attribute | Primary key + metadata | |

**User's choice:** (session_id, cwd) composite key
**Notes:** Allows grouping sessions by project and handles the case of the same session_id in different directories.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Time-based expiry in later phase | Phase 1 creates sessions, Phase 4 cleans up | ✓ |
| Implicit end on Stop event | Stop hook marks session ended | |
| No lifecycle in Phase 1 | Only store metadata and route events | |

**User's choice:** Time-based expiry in a later phase
**Notes:** SessionStart creates a record with last-seen timestamp. Cleanup deferred to Phase 4 (abnormal-state detection).

---

## Hook Merge Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Deep-merge into hooks key only | Preserve all other settings, merge only under hooks | ✓ |
| Single notifier hook key | One entry routing all events internally | |
| Full replace | Destructive — write entire hooks section | |

**User's choice:** Deep-merge into hooks key only
**Notes:** Safety-first. Preserves unrelated user hooks and all non-hook settings.

---

| Option | Description | Selected |
|--------|-------------|----------|
| One entry per event type (4 entries) | Separate config per hook event, clearer in settings.json | ✓ |
| Single entry with wildcard matcher | One hook entry matching all 4 types | |
| Single entry, internal routing | One entry, CLI inspects stdin to route | |

**User's choice:** One entry per event type (4 entries)
**Notes:** Explicit, debuggable. Each entry labeled by event type. Uninstall cleans up all 4.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Marker key in hook entry | `_notifier: true` in each entry | |
| Separate notifier config file | Notifier maintains its own ownership registry | ✓ |
| Convention-based: match command path | Any entry pointing to notifier CLI is owned | |

**User's choice:** Separate notifier config file
**Notes:** Clean separation. Notifier needs its own config file anyway for other settings.

---

## IPC Bridge

| Option | Description | Selected |
|--------|-------------|----------|
| File-based: write events to watched directory | watchdog-based, survives restarts | |
| Local TCP socket (localhost) | Low latency, Python async support | ✓ |
| Named pipe (Windows) | Kernel-buffered, no filesystem overhead | |

**User's choice:** Local TCP socket (localhost)
**Notes:** Clean async model in Python. Good latency. Notifier must be running for events to deliver.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Retry with backoff, then drop | ~3 attempts over ~5s, then log and drop | ✓ |
| Spillover to file on failure | Write to spillover directory, read on startup | |
| Block until notifier available | Indefinite retry — violates hook speed constraint | |

**User's choice:** Retry with backoff, then drop
**Notes:** Keeps hooks fast. Spillover considered but not needed for v1 — notifier is expected to be running during active use.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Newline-delimited JSON (NDJSON) | One JSON line per event, \n terminated | ✓ |
| Length-prefixed JSON frames | 4-byte length + payload, more robust | |
| Plain JSON, one connection per event | Open/send/close per event, no framing | |

**User's choice:** Newline-delimited JSON (NDJSON)
**Notes:** Standard streaming pattern. Simple to produce and consume. Supports connection reuse.

---

## Claude's Discretion

No areas were deferred to Claude — all decisions were explicitly captured by the user.

## Deferred Ideas

None — discussion stayed within Phase 1 scope.

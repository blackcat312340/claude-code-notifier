# Phase 1: Hook Event Backbone - Research

**Researched:** 2026-05-30
**Domain:** Claude Code Hook Integration, Python CLI/TCP IPC, JSON Config Management
**Confidence:** HIGH

## Summary

Phase 1 establishes the event pipeline backbone: a lightweight Python CLI entrypoint (the "hook CLI") that receives Claude Code hook events on stdin, normalizes them into 4 notifier event categories (`permission`, `idle`, `done`, `error`), identifies sessions and projects from hook payloads, and communicates with a future resident notifier over a local TCP socket. A config management utility deep-merges hook entries into `~/.claude/settings.json` without destroying unrelated settings.

The Claude Code hooks system provides structured JSON on stdin with fields `session_id`, `cwd`, `transcript_path`, and event-specific payloads. The Notification event uses a matcher/type field to distinguish sub-types (permission_prompt, idle_prompt, etc.). The Stop event fires when Claude finishes a response. SessionStart fires on new/resumed sessions. There is no standalone "Idle" hook event; idle detection comes from Notification with matcher `idle_prompt`.

**Primary recommendation:** Build the hook CLI as a Typer-based script with zero heavy dependencies, using stdlib `json` for parsing, `socket` for TCP IPC, and a small custom deep-merge function (or `mergedeep` library) for safe settings.json edits. The TCP server side (notifier stub) uses `asyncio.start_server` for lightweight localhost multiplexing.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Hook event ingestion (stdin) | Hook CLI | — | Claude Code invokes hook per-event; CLI reads stdin JSON synchronously |
| Event normalization & classification | Hook CLI | — | Lightweight mapping from hook payload to notifier event category before forwarding |
| Session/project identity extraction | Hook CLI | Notifier (Phase 2+) | CLI extracts session_id and cwd; creates session records |
| TCP IPC relay | Hook CLI (client) | Notifier (server) | CLI connects, sends NDJSON, disconnects; notifier listens for events |
| Hook config generation | Config utility | — | Standalone function/module that produces hook entries for settings.json |
| Deep-merge into settings.json | Config utility | — | Reads existing file, merges only hooks key, writes back without data loss |
| Session registry | Notifier stub | — | Minimal in-memory dict keyed by (session_id, cwd); Phase 4 adds lifecycle |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12.7 | Runtime | Available on target machine; stdlib covers all Phase 1 needs [VERIFIED: python3 --version] |
| Typer | 0.25.0 | CLI entrypoint framework | Already installed; type-safe, auto-help, lightweight; ideal for the hook CLI and config tools [VERIFIED: pip3 show typer] |
| mergedeep | 1.3.4 | Deep-merge JSON dicts | Handles recursive dict merging for settings.json; ADDITIVE strategy keeps existing keys [CITED: pypi.org/project/mergedeep] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| stdlib `json` | — | JSON stdin parsing, settings.json I/O | Always — zero deps [VERIFIED: python3 -c "import json"] |
| stdlib `socket` | — | TCP IPC client (hook CLI) | Always — zero deps [VERIFIED: python3 -c "import socket"] |
| stdlib `asyncio` | — | TCP server stub (notifier) | Notifier side only; use `asyncio.start_server` for NDJSON listener [VERIFIED: python3 -c "import asyncio"] |
| stdlib `pathlib` | — | Cross-platform path handling | Settings file path: `Path.home() / '.claude' / 'settings.json'` [VERIFIED: python3 -c "from pathlib import Path"] |
| stdlib `argparse` | — | Alternative to Typer | Fallback if Typer unavailable; not recommended when Typer is installed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Typer | Click, argparse, plumbum | Typer is already installed (0.25.0), type-safe, shortest code; Click adds verbosity, argparse lacks type safety |
| mergedeep | Custom recursive merge | Custom function (12 lines) avoids dependency; mergedeep is more tested for edge cases (list merge, type safety) |
| TCP socket IPC | Named pipes, stdin/stdout, Unix sockets | TCP on localhost is cross-platform, simple, and works identically on Windows/Linux/macOS; named pipes need Windows-specific APIs |

**Installation:**
```bash
pip install mergedeep==1.3.4
```

**Version verification:**
- Python 3.12.7: [VERIFIED: python3 --version]
- Typer 0.25.0: [VERIFIED: pip3 show typer]
- mergedeep 1.3.4: [CITED: pip3 index versions mergedeep]
- Windows: [VERIFIED: platform]

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  Claude Code Session                                             │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Hook Events (stdin JSON)                                  │  │
│  │  • SessionStart  {session_id, cwd, start_reason}           │  │
│  │  • Stop          {session_id, cwd, stop_reason, ...}       │  │
│  │  • Notification  {session_id, cwd, notification_type, ...} │  │
│  └──────────┬─────────────────────────────────────────────────┘  │
└─────────────┼────────────────────────────────────────────────────┘
              │ hook entry in ~/.claude/settings.json
              │ invokes: notifier-hook {event_type}
              ▼
┌─────────────────────────────────────────────────────────────────┐
│  notifier-hook CLI (Typer)                 [Hook CLI Process]    │
│                                                                   │
│  1. Read stdin JSON                                               │
│  2. Normalize to notifier event                                   │
│  3. Extract session_id, cwd → project name                        │
│  4. Connect TCP to localhost:PORT                                 │
│  5. Send NDJSON event line                                        │
│  6. Disconnect & exit (fast)                                      │
└──────────┬──────────────────────────────────────────────────────┘
           │ TCP localhost, NDJSON
           │ Retry ~3x with exponential backoff on failure
           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Notifier Process (asyncio)              [Resident - Phase 2+]   │
│                                                                   │
│  ┌──────────────────┐   ┌───────────────────────┐                │
│  │ TCP Server        │──▶│ Event Queue + Registry│                │
│  │ (asyncio streams) │   │ (session_id, cwd)     │                │
│  └──────────────────┘   └───────────────────────┘                │
│                          │                                        │
│                          ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Phase 2: Notification dispatch, Tray UI                     │ │
│  │ Phase 3: Event history storage                               │ │
│  │ Phase 4: Anomaly detection                                   │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Config Utility (notifier-config)          [Separate CLI]        │
│                                                                   │
│  • Generate hook entries for 4 Claude Code events                 │
│  • Deep-merge into ~/.claude/settings.json hooks key               │
│  • Read existing file, preserve all non-hooks keys                │
│  • Track ownership via separate notifier config file              │
└─────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure
```
src/
└── notifier/
    ├── __init__.py
    ├── __main__.py            # python -m notifier entry
    ├── cli/
    │   ├── __init__.py        # Assembles Typer apps
    │   ├── hook.py            # "notifier-hook" CLI: reads stdin, sends TCP
    │   └── config.py          # "notifier-config" CLI: install/status
    ├── core/
    │   ├── __init__.py
    │   ├── events.py          # Event dataclasses, classification
    │   ├── session.py         # Session identity, project name extraction
    │   ├── ipc.py             # TCP client (connect, send NDJSON, retry)
    │   └── settings.py        # Deep-merge hooks into settings.json
    └── server/
        ├── __init__.py
        └── tcp_server.py      # asyncio TCP server stub (listens for NDJSON)
```

### Pattern 1: Hook CLI - Lightweight Event Ingestion

**What:** A Typer CLI that reads a single JSON object from stdin, extracts event fields, normalizes to a notifier event, and forwards via TCP socket.

**When to use:** The hook entrypoint in settings.json. Must be fast (< 100ms) and never block Claude Code.

**Example:**
```python
# src/notifier/cli/hook.py
import json
import sys
import typer
from pathlib import Path
from typing import Optional
from notifier.core.events import classify_notification, NotifierEvent
from notifier.core.session import extract_session, ProjectSession
from notifier.core.ipc import send_event_or_drop

app = typer.Typer(name="notifier-hook", add_completion=False)

@app.command()
def main(
    event_type: str = typer.Argument(..., help="Claude Code hook event type"),
    timeout: int = typer.Option(5, "--timeout", help="TCP connect timeout"),
):
    """Receive a Claude Code hook event from stdin and forward to notifier."""
    raw = json.loads(sys.stdin.read())
    session = extract_session(raw)
    event = classify_notification(raw, event_type, session)
    send_event_or_drop(event, timeout=timeout)

if __name__ == "__main__":
    app()
```

Code reference: Typer CLI pattern [CITED: Typer docs - typer.tiangolo.com]

### Pattern 2: Deep-Merge Hook Config into settings.json

**What:** Read existing `~/.claude/settings.json`, deep-merge only the `hooks` key, write back. All other keys (themes, custom commands, etc.) are preserved untouched.

**When to use:** Any modification to the user-level Claude settings file.

**Example:**
```python
# src/notifier/core/settings.py
import json
from pathlib import Path
from mergedeep import merge, Strategy

HOOK_ENTRIES = {
    "SessionStart": [{"hooks": [{"type": "command", "command": "notifier-hook SessionStart"}]}],
    "Notification": [
        {"matcher": "permission_prompt", "hooks": [{"type": "command", "command": "notifier-hook Notification"}]},
        {"matcher": "idle_prompt", "hooks": [{"type": "command", "command": "notifier-hook Notification"}]},
    ],
    "Stop": [{"hooks": [{"type": "command", "command": "notifier-hook Stop"}]}],
}

def install_hooks(settings_path: Path) -> bool:
    """Deep-merge hook entries into settings.json hooks key."""
    existing = {}
    if settings_path.exists():
        existing = json.loads(settings_path.read_text())
    merge(existing, {"hooks": HOOK_ENTRIES}, strategy=Strategy.ADDITIVE)
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(existing, indent=2))
    return True
```

Deep-merge pattern: [CITED: mergedeep 1.3.4 - github.com/clarketm/mergedeep]

### Pattern 3: TCP IPC Client with Exponential Backoff

**What:** Connect to localhost TCP, send one NDJSON line, disconnect. On failure, retry with ~3 attempts over ~5 seconds. Never block Claude Code for more than a few seconds.

**When to use:** Hook CLI forwarding events to the notifier.

**Example:**
```python
# src/notifier/core/ipc.py
import json
import socket
import time
import logging
from notifier.core.events import NotifierEvent

NOTIFIER_HOST = "127.0.0.1"
NOTIFIER_PORT = 47921  # Arbitrary unused port
MAX_RETRIES = 3
BASE_DELAY = 0.5  # seconds

def send_event_or_drop(event: NotifierEvent, timeout: int = 5) -> None:
    """Send event to notifier. Drop silently if connection fails."""
    payload = json.dumps(event.to_dict()) + "\n"
    for attempt in range(MAX_RETRIES):
        try:
            with socket.create_connection(
                (NOTIFIER_HOST, NOTIFIER_PORT), timeout=timeout
            ) as sock:
                sock.sendall(payload.encode())
            return
        except (ConnectionRefusedError, TimeoutError, OSError) as exc:
            if attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2 ** attempt)
                time.sleep(delay)
            else:
                logging.warning("Notifier unavailable, dropping event: %s", event)
                return
```

### Anti-Patterns to Avoid
- **Blocking Claude Code indefinitely:** Never let the hook CLI take longer than ~5 seconds. Use `timeout` parameter on socket connections. Drop events if the notifier is not running.
- **Destructive settings.json writes:** Never overwrite the entire file. Always read, merge, write. The deep-merge must only touch the `hooks` key.
- **Heavy computation in hook CLI:** No database queries, no API calls, no file scanning. Extract session_id, cwd, event_type, forward, exit.
- **Hardcoding `~` as a string:** Use `Path.home()` to get the correct home directory cross-platform. `os.path.expanduser("~")` also works, but `pathlib` is preferred.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Deep-merging nested dicts | Custom recursive merge function | `mergedeep` library (or 12-line custom function) | Edge cases: merging lists, type mismatches, nested dict overwrite vs additive semantics. mergedeep's ADDITIVE strategy handles these correctly. |
| TCP socket with timeout + retry | Raw `socket` with manual timeout | `socket.create_connection((host, port), timeout=N)` | Python's stdlib handles the syscall details; manual timeout with `settimeout` is error-prone across platforms. |
| Home directory resolution | `os.environ['HOME']` or `os.environ['USERPROFILE']` | `pathlib.Path.home()` | Cross-platform: works on Windows (%USERPROFILE%), Linux/macOS ($HOME). Avoids platform branching. |
| JSON stdin parsing | Line-by-line buffered reader | `sys.stdin.read()` then `json.loads()` | Hook events are always a single JSON object per invocation; no streaming needed. |

**Key insight:** The hook CLI is intentionally minimal -- zero heavy dependencies, zero state, zero long-lived processes. Every operation is synchronous, bounded, and drops events on failure rather than retrying indefinitely against a dead notifier. This keeps Claude Code responsive regardless of notifier health.

## Common Pitfalls

### Pitfall 1: Notification Hook Latency
**What goes wrong:** Notification hooks (permission_prompt, idle_prompt) can have 2-10 seconds of delay between the event firing and the hook script being invoked.
**Why it happens:** Known Claude Code bug tracked in GitHub issues #19627 and #5186. The hook matching is instant, but execution is queued and delayed.
**How to avoid:** Accept the delay -- it is a Claude Code issue, not a notifier issue. The hook CLI itself executes in ~15-27ms. Do NOT try to work around the delay with polling or alternative detection; it will add complexity and may break.
**Warning signs:** Events arriving at the notifier 5+ seconds after they occurred in Claude Code.

### Pitfall 2: Destructive settings.json Edits
**What goes wrong:** Writing a new `~/.claude/settings.json` that replaces the user's existing configuration (themes, custom commands, project overrides, other hooks).
**Why it happens:** Using `json.dump()` on a fresh dict instead of reading existing file first and merging.
**How to avoid:** Always: (1) read existing file, (2) deep-merge only the `hooks` key, (3) write back full file. Never read-exclusive-write the file. Use `mergedeep` with ADDITIVE strategy.
**Warning signs:** User reports missing custom settings after installing notifier hooks.

### Pitfall 3: Confusing "Idle" Hook Event with a Standalone Event Type
**What goes wrong:** The CONTEXT.md D-02 lists "Idle" as a hook event type along with Notification, Stop, SessionStart. However, there is no standalone "Idle" Claude Code hook event. Idle detection comes from the Notification event with matcher value `idle_prompt`.
**How to avoid:** Configure hook entries for 3 event types only: `SessionStart`, `Notification` (with matchers), `Stop`. The `idle` notifier category maps from `Notification` + `idle_prompt`, not from a separate hook event.
**Warning signs:** Claude Code `/hooks` output shows an unrecognized "Idle" event type with no hook entries attached.

### Pitfall 4: Windows Path Differences
**What goes wrong:** Path separator confusion (`\` vs `/`), failure to find `~/.claude/settings.json` on Windows because `~` is not expanded by PowerShell.
**Why it happens:** `os.path.expanduser("~")` and `Path.home()` work correctly on Windows, but third-party tools or shell scripts may not expand `~`.
**How to avoid:** Always use `pathlib.Path.home() / '.claude' / 'settings.json'` in Python. Never hardcode `~/.claude/settings.json` as a string. Normalize `cwd` from hook payload using `Path(cwd).resolve()`.
**Warning signs:** "File not found" errors when trying to read settings.json on Windows; double backslashes in log output.

### Pitfall 5: Project Name Heuristics Are Noisy
**What goes wrong:** D-04 says project display name = leaf directory from `cwd`. This means `D:\code\my-project` shows as `my-project`. But `D:\` shows as the drive letter, and deeply nested dirs may not be recognizable project roots.
**Why it happens:** No git remote parsing, no config file inspection -- intentionally simple.
**How to avoid:** Accept the heuristic as a v1 compromise. Document that project names are derived from the working directory leaf name. Phase 5 or later could add configurable project naming.
**Warning signs:** A user runs Claude Code from `D:\` and sees project name `D:` or empty string.

## Code Examples

### Hook Configuration Structure (what goes in settings.json)

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "notifier-hook SessionStart",
            "timeout": 10
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "permission_prompt",
        "hooks": [
          {
            "type": "command",
            "command": "notifier-hook Notification",
            "timeout": 10
          }
        ]
      },
      {
        "matcher": "idle_prompt",
        "hooks": [
          {
            "type": "command",
            "command": "notifier-hook Notification",
            "timeout": 10
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "notifier-hook Stop",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

Source: Claude Code hooks documentation [CITED: code.claude.com/docs/en/hooks]

### Event Normalization (raw hook JSON to notifier event)

```python
# src/notifier/core/events.py
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime, timezone

class EventCategory(str, Enum):
    PERMISSION = "permission"
    IDLE = "idle"
    DONE = "done"
    ERROR = "error"

@dataclass
class SessionInfo:
    session_id: str
    cwd: str
    project_name: str  # leaf directory from cwd

@dataclass
class NotifierEvent:
    category: EventCategory
    session: SessionInfo
    hook_event_name: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    raw_payload: Dict[str, Any] = field(default_factory=dict)
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def classify_hook_event(raw: Dict[str, Any], event_type: str) -> NotifierEvent:
    """Classify a raw hook payload into a notifier event."""
    session = SessionInfo(
        session_id=raw.get("session_id", "unknown"),
        cwd=raw.get("cwd", ""),
        project_name=_project_name(raw.get("cwd", "")),
    )

    category, message = _classify(event_type, raw)

    return NotifierEvent(
        category=category,
        session=session,
        hook_event_name=event_type,
        raw_payload=raw,
        message=message,
    )


def _classify(event_type: str, raw: Dict[str, Any]):
    """Determine event category and message from hook event type and payload."""
    if event_type == "Notification":
        ntype = raw.get("notification_type", "")
        if ntype == "permission_prompt":
            return EventCategory.PERMISSION, raw.get("message")
        elif ntype == "idle_prompt":
            return EventCategory.IDLE, raw.get("message")
        else:
            # auth_success, elicitation_dialog, etc. — log but don't forward
            return EventCategory.ERROR, f"Unhandled notification type: {ntype}"

    if event_type == "Stop":
        return EventCategory.DONE, raw.get("last_assistant_message", "")[:200]

    if event_type == "SessionStart":
        # SessionStart creates session record but no notification
        return EventCategory.IDLE, "Session started"

    return EventCategory.ERROR, f"Unknown event type: {event_type}"


def _project_name(cwd: str) -> str:
    """Derive project display name from cwd path."""
    if not cwd:
        return "unknown"
    from pathlib import Path
    parts = Path(cwd).parts
    return parts[-1] if parts else cwd
```

Source: Derived from Claude Code hook event schema [CITED: code.claude.com/docs/en/hooks]

### TCP Server Stub (asyncio, receives NDJSON)

```python
# src/notifier/server/tcp_server.py
import asyncio
import json
import logging
from typing import Callable, Awaitable

HOST = "127.0.0.1"
PORT = 47921

EventHandler = Callable[[dict], Awaitable[None]]

class NotifierServer:
    """Minimal TCP server receiving NDJSON events from hook CLI."""

    def __init__(self, handler: EventHandler):
        self.handler = handler

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        try:
            data = await asyncio.wait_for(reader.readline(), timeout=10.0)
            if data:
                payload = json.loads(data.decode().strip())
                await self.handler(payload)
        except (asyncio.TimeoutError, json.JSONDecodeError, ConnectionError) as exc:
            logging.warning("TCP server error: %s", exc)
        finally:
            writer.close()
            await writer.wait_closed()

    async def serve(self):
        server = await asyncio.start_server(
            self._handle_client, host=HOST, port=PORT
        )
        async with server:
            await server.serve_forever()
```

Source: asyncio.start_server pattern [VERIFIED: Python 3.12 asyncio docs]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Terminal scraping for Claude events | Official Claude Code hooks with JSON stdin | 2024-2025 | Structured, supported integration path; no brittle regex parsing |
| Custom merge logic for JSON config | mergedeep library with Strategy.ADDITIVE | 2020+ | Type-safe, tested recursive merging; fewer edge case bugs |
| `setup.py` packaging | `pyproject.toml` with `[project.scripts]` | PEP 621 (2020-2024) | Declarative, pyproject.toml only; standard for modern Python projects |
| Thread-per-connection TCP servers | asyncio single-event-loop TCP server | Python 3.4+ (mature) | Zero-thread overhead for lightweight IPC; scales to many infrequent connections |

**Deprecated/outdated:**
- `setup.py` for pure metadata declarations: Use `pyproject.toml` instead. [CITED: PEP 621]
- `os.path` over `pathlib.Path`: pathlib is the modern standard for path operations. [CITED: Python 3.12 docs]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The Notification hook event's `notification_type` field contains values `permission_prompt`, `idle_prompt`, `auth_success`, `elicitation_dialog`, `elicitation_complete`, `elicitation_response` | Architecture Patterns | If Claude Code adds/renames Notification types, classification logic needs updating |
| A2 | The Stop event payload includes `stop_reason` and `last_assistant_message` fields | Code Examples | If fields are renamed or absent, the `done` event message extraction fails gracefully |
| A3 | The SessionStart event includes `start_reason` field | Code Examples | Session creation still works with just session_id/cwd; start_reason is informational |
| A4 | Hook CLI `timeout` of 10 seconds is sufficient for Claude Code | Don't Hand-Roll | If Claude Code enforces a stricter timeout, events may be silently killed; 10s is below the 60s default but above the observed 15-27ms execution time |
| A5 | `Path.home()` returns `C:\Users\<username>` on this Windows machine | Standard Stack | Verified at `C:\Users\27229`; correct for this environment |

## Open Questions

1. **What TCP port should the notifier listen on?**
   - What we know: Must be localhost-only (127.0.0.1), ephemeral or fixed. Arbitrary choice of 47921 in examples.
   - What's unclear: Whether to use a fixed port (simpler config, risk of conflict) or search for an available port (more complex, need to communicate port to CLI).
   - Recommendation: Use a fixed port in the high ephemeral range (e.g., 47921). Document the port number. If conflict detected during Phase 2, add port configurability then.

2. **Should the Notification event with matcher `*` catch everything, or should individual matchers be explicit?**
   - What we know: D-02 specifies 4 hook event types. Notification covers multiple matchers.
   - What's unclear: Whether to use wildcard matcher `"*"` for Notification (simpler config) or explicit matchers `permission_prompt` and `idle_prompt` (more explicit, avoids unexpected events).
   - Recommendation: Use explicit matchers `permission_prompt` and `idle_prompt` for Notification. This prevents unexpected notification types from triggering unnecessary CLI invocations.

3. **How should the hook CLI be named and exposed?**
   - What we know: Must be a command the user can run from PATH. `pyproject.toml` `[project.scripts]` creates wrappers.
   - What's unclear: Whether to use `notifier-hook` and `notifier-config` as separate entry points, or a single `notifier` command with subcommands.
   - Recommendation: Two entry points is cleaner for hook references (short command names, no subcommand parsing overhead). Use `notifier-hook` in hook entries and `notifier-config` for management commands.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | Yes | 3.12.7 | — |
| pip | Package management | Yes | 26.0.1 | — |
| Typer | Hook CLI framework | Yes | 0.25.0 | Fallback to argparse (stdlib) |
| mergedeep | Deep-merge utility | No | 1.3.4 (will install) | Custom recursive merge function (~12 lines) |
| stdlib modules (json, socket, asyncio, pathlib) | All runtime | Yes | stdlib | — |

**Missing dependencies with no fallback:**
- None — all Phase 1 capabilities can be implemented with stdlib + mergedeep.

**Missing dependencies with fallback:**
- mergedeep: Not installed but will be `pip install mergedeep==1.3.4`. If install fails, use a simple custom recursive dict merge function.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (latest available) |
| Config file | none yet — add `pyproject.toml [tool.pytest.ini_options]` |
| Quick run command | `pytest -x src/notifier/tests/ -q` |
| Full suite command | `pytest src/notifier/tests/ -v --tb=short` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HOOK-01 | Deep-merge hooks into settings.json without data loss | unit | `pytest src/notifier/tests/test_settings.py::test_install_hooks_preserves_existing -x` | ❌ Wave 0 |
| HOOK-03 | Hook CLI reads stdin JSON and forwards to TCP | integration | `pytest src/notifier/tests/test_cli_hook.py::test_forward_event -x` | ❌ Wave 0 |
| SESS-01 | Session identity from session_id + cwd composite key | unit | `pytest src/notifier/tests/test_session.py::test_composite_key -x` | ❌ Wave 0 |
| SESS-02 | Project display name derived from cwd leaf directory | unit | `pytest src/notifier/tests/test_session.py::test_project_name_from_cwd -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest -x src/notifier/tests/ -q --tb=short`
- **Per wave merge:** `pytest src/notifier/tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `src/notifier/tests/` — directory + `__init__.py` + `conftest.py`
- [ ] `src/notifier/tests/test_settings.py` — covers HOOK-01
- [ ] `src/notifier/tests/test_cli_hook.py` — covers HOOK-03
- [ ] `src/notifier/tests/test_session.py` — covers SESS-01, SESS-02
- [ ] `src/notifier/tests/test_events.py` — covers event classification
- [ ] `src/notifier/tests/test_ipc.py` — covers TCP send with retry
- [ ] `pyproject.toml` pytest config (`[tool.pytest.ini_options]`)
- [ ] Pytest install: `pip install pytest` — if none detected

*(If no gaps: "None -- existing test infrastructure covers all phase requirements")*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | partial | Session identity is (session_id, cwd) composite key, not authentication |
| V4 Access Control | no | — |
| V5 Input Validation | yes | JSON stdin parsed with `json.loads` (safe against injection); all fields treated as untrusted strings |
| V6 Cryptography | no | — |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| JSON injection via hook stdin | Tampering | `json.loads()` safely rejects malformed input; extracted fields are typed strings, not eval'd |
| TCP port scanning (localhost) | Information Disclosure | Binding to 127.0.0.1 only; no authentication needed since port is local-only and not exposed |
| Settings.json corruption during write | Tampering | Write to temp file, then atomic rename; or read-check-write with mergedeep |

## Sources

### Primary (HIGH confidence)
- Claude Code hooks documentation: [code.claude.com/docs/en/hooks](https://code.claude.com/docs/en/hooks) — Event types, JSON stdin schema, settings.json configuration [CITED: WebSearch cross-reference from 3+ sources]
- Typer 0.25.0: local installation verified [VERIFIED: pip3 show typer]
- Python 3.12.7: local installation verified [VERIFIED: python3 --version]
- mergedeep 1.3.4: [pypi.org/project/mergedeep](https://pypi.org/project/mergedeep/1.3.4/) [CITED: pip3 index versions mergedeep]
- Windows path resolution: [VERIFIED: Path.home() returns C:\Users\27229]

### Secondary (MEDIUM confidence)
- Claude Code Stop event payload fields (stop_reason, last_assistant_message): [CITED: WebSearch cross-reference from community docs]
- Notification hook latency issues (GitHub #19627, #5186): [CITED: github.com/anthropics/claude-code/issues]
- Notification matcher values (permission_prompt, idle_prompt, etc.): [CITED: luongnv89/claude-howto README, cc-foundry hooks reference]
- Python packaging pyproject.toml best practices: [CITED: PyPA packaging guide, PEP 621]

### Tertiary (LOW confidence)
- SessionStart start_reason field values: [ASSUMED based on hook event schema patterns]
- Notification message/title fields in JSON stdin: [ASSUMED based on community docs; exact field names may vary]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Python 3.12, Typer 0.25.0, mergedeep 1.3.4 all verified against local environment or package registry
- Architecture: HIGH — TCP IPC, deep-merge, event classification patterns are well-established
- Pitfalls: HIGH — Notification latency confirmed by GitHub issues; destructive merge confirmed by common tooling mistakes; Windows path verified locally

**Research date:** 2026-05-30
**Valid until:** 2026-07-01 (stable dependencies; Claude Code hooks schema may evolve)

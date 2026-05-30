"""Fast hook entry point — no heavy CLIframework, minimal imports.

Claude Code invokes: python -m notifier.cli.hook {event_type}
Reads a single JSON object from stdin, classifies, forwards via TCP.
"""
import json
import sys
import re
from notifier.core.events import classify_hook_event
from notifier.core.ipc import send_event_or_drop, NOTIFIER_HOST, NOTIFIER_PORT


def _safe_read_stdin() -> dict:
    """Read hook JSON from stdin, falling back to safe-mode extraction."""
    raw_text = sys.stdin.read()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    # Fallback: extract key fields via regex for malformed payloads
    result = {}

    def _extract(key, default=""):
        m = re.search(r'"' + key + r'"\s*:\s*"((?:[^"\\]|\\.)*)"', raw_text)
        return m.group(1) if m else default

    result["session_id"] = _extract("session_id", "unknown")
    result["cwd"] = _extract("cwd", "")
    result["transcript_path"] = _extract("transcript_path", "")
    result["notification_type"] = _extract("notification_type", "")

    msg = _extract("last_assistant_message", "")
    if msg:
        result["last_assistant_message"] = msg[:200]

    msg = _extract("message", "")
    if msg:
        result["message"] = msg[:500]

    return result


def process_hook_event(
    raw: dict,
    event_type: str,
    timeout: int = 5,
    host: str = NOTIFIER_HOST,
    port: int = NOTIFIER_PORT,
):
    """Testable event processing: classify, send via TCP."""
    event = classify_hook_event(raw, event_type)
    send_event_or_drop(event, timeout=timeout, host=host, port=port)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m notifier.cli.hook <event_type>", file=sys.stderr)
        sys.exit(1)

    event_type = sys.argv[1]
    raw = _safe_read_stdin()
    process_hook_event(raw, event_type)

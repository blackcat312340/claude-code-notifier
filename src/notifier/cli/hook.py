import json
import sys
import logging
import typer
from notifier.core.events import classify_hook_event
from notifier.core.session import extract_session
from notifier.core.ipc import send_event_or_drop, NOTIFIER_HOST, NOTIFIER_PORT

app = typer.Typer(name="notifier-hook", add_completion=False)


def _safe_read_stdin() -> dict:
    """Read hook JSON from stdin, falling back to safe-mode extraction.

    Claude Code Stop events include last_assistant_message which may
    contain unescaped characters that break JSON parsing. We attempt
    strict parse first, then fall back to extracting key fields via
    regex if the payload is malformed.
    """
    raw_text = sys.stdin.read()

    # Try strict parse first
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    # Fallback: extract what we can — session_id, cwd, and key event fields
    import re
    result = {}

    def _extract_str(key, default=""):
        # Match "key": "value" — handles escaped quotes in value
        m = re.search(r'"' + key + r'"\s*:\s*"((?:[^"\\]|\\.)*)"', raw_text)
        return m.group(1) if m else default

    result["session_id"] = _extract_str("session_id", "unknown")
    result["cwd"] = _extract_str("cwd", "")
    result["transcript_path"] = _extract_str("transcript_path", "")
    result["notification_type"] = _extract_str("notification_type", "")

    # For Stop events, extract truncated last_assistant_message
    msg = _extract_str("last_assistant_message", "")
    if msg:
        result["last_assistant_message"] = msg[:200]  # truncate for safety

    # Extract message field (for Notification events)
    msg = _extract_str("message", "")
    if msg:
        result["message"] = msg[:500]

    logging.warning("Hook JSON parse failed — extracted keys via safe fallback")
    return result


@app.command()
def main(
    event_type: str = typer.Argument(
        ..., help="Claude Code hook event type (Notification, Stop, SessionStart)"
    ),
    timeout: int = typer.Option(5, "--timeout", help="TCP connect timeout"),
):
    """Receive a Claude Code hook event from stdin and forward to notifier.

    Hook entry command: notifier-hook {event_type}
    Reads a single JSON object from stdin (per Claude Code's per-invocation pattern).
    """
    raw = _safe_read_stdin()
    process_hook_event(raw, event_type, timeout=timeout)


def process_hook_event(
    raw: dict,
    event_type: str,
    timeout: int = 5,
    host: str = NOTIFIER_HOST,
    port: int = NOTIFIER_PORT,
):
    """Testable event processing: classify session, build event, send via IPC.

    This function exists separately from the CLI entry point so tests
    can call it directly without piping stdin.
    """
    event = classify_hook_event(raw, event_type)
    send_event_or_drop(event, timeout=timeout, host=host, port=port)


if __name__ == "__main__":
    app()

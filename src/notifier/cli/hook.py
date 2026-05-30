import json
import sys
import typer
from notifier.core.events import classify_hook_event
from notifier.core.session import extract_session
from notifier.core.ipc import send_event_or_drop, NOTIFIER_HOST, NOTIFIER_PORT

app = typer.Typer(name="notifier-hook", add_completion=False)


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
    raw = json.loads(sys.stdin.read())
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

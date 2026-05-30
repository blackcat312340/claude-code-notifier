import json
import socket
import time
import logging
from typing import Optional
from notifier.core.events import NotifierEvent

NOTIFIER_HOST = "127.0.0.1"
NOTIFIER_PORT = 47921
MAX_RETRIES = 3
BASE_DELAY = 0.5  # seconds


def send_event_or_drop(
    event: NotifierEvent,
    timeout: int = 5,
    host: str = NOTIFIER_HOST,
    port: int = NOTIFIER_PORT,
) -> None:
    """Send event to notifier over TCP. Drop silently if unavailable.

    Per D-10: TCP localhost IPC.
    Per D-11: Retry with exponential backoff (~3 attempts over ~5s), then drop.
    Per D-12: NDJSON wire format.

    Args:
        event: The event to send.
        timeout: Socket connect timeout in seconds.
        host: TCP host (default 127.0.0.1).
        port: TCP port (default 47921).
    """
    payload = json.dumps(event.to_dict()) + "\n"
    for attempt in range(MAX_RETRIES):
        try:
            with socket.create_connection(
                (host, port), timeout=timeout
            ) as sock:
                sock.sendall(payload.encode())
            return
        except (ConnectionRefusedError, TimeoutError, OSError) as exc:
            if attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2**attempt)
                time.sleep(delay)
            else:
                logging.warning(
                    "Notifier unavailable, dropping event: %s (type=%s, session=%s)",
                    event.hook_event_name,
                    event.category.value,
                    event.session.session_id,
                )
                return

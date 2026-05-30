import logging
import subprocess
import sys
import json
import time
from typing import Dict, Set, Tuple
from notifier.core.events import EventCategory, NotifierEvent

NOTIFY_COOLDOWN_S = 30

# D-05: Only PERMISSION, IDLE, DONE fire notifications. ERROR is logged only.
NOTIFY_CATEGORIES: Set[EventCategory] = {
    EventCategory.PERMISSION,
    EventCategory.IDLE,
    EventCategory.DONE,
}

# In-memory cooldown tracker: {(project_name, category): last_notification_timestamp}
_cooldowns: Dict[Tuple[str, str], float] = {}


def _category_value(category):
    """Extract string value from EventCategory enum or plain string."""
    if isinstance(category, EventCategory):
        return category.value
    return str(category)


def _check_cooldown(project_name: str, category: EventCategory) -> bool:
    """Return True if enough time has passed since last notification for this key.

    Per D-06: 30 second cooldown per (project_name, category) composite key.
    """
    key = (project_name, _category_value(category))
    now = time.monotonic()
    last = _cooldowns.get(key, 0.0)
    if now - last >= NOTIFY_COOLDOWN_S:
        _cooldowns[key] = now
        return True
    return False


def _build_body(event: NotifierEvent) -> str:
    """Build notification body text per D-04 format rules.

    PERMISSION: "Permission needed - {message or 'Claude needs your attention'}"
    IDLE: "Waiting for input - {message or 'Claude is idle and awaiting further instructions'}"
    DONE: "Task complete - {message[:200] or 'Claude finished the current task'}"
    """
    if event.category == EventCategory.PERMISSION:
        detail = event.message or "Claude needs your attention"
        return f"Permission needed - {detail}"

    if event.category == EventCategory.IDLE:
        detail = event.message or "Claude is idle and awaiting further instructions"
        return f"Waiting for input - {detail}"

    if event.category == EventCategory.DONE:
        detail = (event.message or "Claude finished the current task")[:200]
        return f"Task complete - {detail}"

    return str(_category_value(event.category))


def dispatch_notification(event: NotifierEvent) -> bool:
    """Fire a Windows desktop notification for the event if warranted.

    Returns True if a notification was shown, False if suppressed
    (wrong category, cooldown active, or notification failure).
    """
    # D-05: Only notify for PERMISSION, IDLE, DONE
    if event.category not in NOTIFY_CATEGORIES:
        if event.category == EventCategory.ERROR:
            logging.info(
                "ERROR event logged (no notification): %s (session=%s)",
                event.hook_event_name,
                event.session.session_id,
            )
        return False

    project = event.session.project_name

    # D-06: 30s cooldown
    if not _check_cooldown(project, event.category):
        logging.debug(
            "Notification suppressed (cooldown): %s/%s",
            project,
            _category_value(event.category),
        )
        return False

    try:
        # D-04: Title = project name, Body = reminder type + context
        # Spawn a subprocess to show the toast — avoids daemon-thread
        # WNDPROC conflicts that prevent notifications from appearing.
        body = _build_body(event)
        subprocess.Popen(
            [
                sys.executable,
                "-c",
                "from win10toast import ToastNotifier; "
                f"ToastNotifier().show_toast({json.dumps(project)}, {json.dumps(body)}, duration=5, threaded=True)",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logging.info(
            "Notification sent: %s | project=%s | category=%s",
            event.hook_event_name,
            project,
            _category_value(event.category),
        )
        return True
    except Exception as exc:
        logging.warning("Notification failed: %s", exc)
        return False

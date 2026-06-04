import logging
import time
from typing import Dict, Set, Tuple

from notifier.core.events import EventCategory, NotifierEvent, Provider
from notifier.core.text import notification_title, notification_body

NOTIFY_COOLDOWN_S = 5

# D-05: Only PERMISSION, IDLE, DONE fire notifications. ERROR is logged only.
NOTIFY_CATEGORIES: Set[EventCategory] = {
    EventCategory.PERMISSION,
    EventCategory.IDLE,
    EventCategory.DONE,
}

# winotify for Windows native toast notifications (WinRT-based, no message pump needed)
from winotify import Notification

# In-memory cooldown tracker: {(provider, project_name, category): last_notification_timestamp}
_cooldowns: Dict[Tuple[str, str, str], float] = {}


def _category_value(category):
    """Extract string value from EventCategory enum or plain string."""
    if isinstance(category, EventCategory):
        return category.value
    return str(category)


def _provider_value(provider):
    """Extract string value from Provider enum or plain string."""
    if isinstance(provider, Provider):
        return provider.value
    return str(provider)


def should_notify(event: NotifierEvent) -> bool:
    """Return True if this event should trigger a desktop notification.

    Per D-08, D-10: SessionStart and ERROR events must not notify.
    Unknown Codex/error records are classified as ERROR upstream and
    are suppressed here as well.
    """
    # ERROR category never notifies (includes unknown Codex events per D-10)
    if event.category == EventCategory.ERROR:
        return False
    # SessionStart never notifies (D-08: session/history update only)
    if event.hook_event_name == "SessionStart":
        return False
    return True


def _check_cooldown(provider: str, project_name: str, category: EventCategory) -> bool:
    """Return True if enough time has passed since last notification for this key.

    Per D-02: cooldown key is provider-aware to avoid Claude Code and Codex
    events suppressing each other for the same project/category.
    """
    key = (provider, project_name, _category_value(category))
    now = time.monotonic()
    last = _cooldowns.get(key, 0.0)
    if now - last >= NOTIFY_COOLDOWN_S:
        _cooldowns[key] = now
        return True
    return False


def _build_body(event: NotifierEvent) -> str:
    """Build notification body text — delegates to centralized Chinese helpers."""
    return notification_body(event)


def dispatch_notification(event: NotifierEvent) -> bool:
    """Fire a Windows desktop notification for the event if warranted.

    Returns True if a notification was shown, False if suppressed
    (wrong category, cooldown active, or notification failure).
    """
    # Per D-08, D-10: event-level notification eligibility
    if not should_notify(event):
        if event.category == EventCategory.ERROR or event.hook_event_name == "SessionStart":
            logging.info(
                "Event suppressed (no notification): %s category=%s (session=%s)",
                event.hook_event_name,
                _category_value(event.category),
                event.session.session_id,
            )
        return False

    provider_str = _provider_value(event.provider)
    project = event.session.project_name

    # Per D-02: provider-aware cooldown
    if not _check_cooldown(provider_str, project, event.category):
        logging.debug(
            "Notification suppressed (cooldown): %s/%s/%s",
            provider_str,
            project,
            _category_value(event.category),
        )
        return False

    try:
        body = notification_body(event)
        Notification(
            app_id="Claude Code Notifier",
            title=notification_title(event),
            msg=body,
            duration="short",
        ).show()
        logging.info(
            "Notification sent: %s | provider=%s | project=%s | category=%s",
            event.hook_event_name,
            provider_str,
            project,
            _category_value(event.category),
        )
        return True
    except Exception as exc:
        logging.warning("Notification failed: %s", exc)
        return False

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Dict, Any, Union
from datetime import datetime, timezone


class Provider(str, Enum):
    CLAUDE_CODE = "claude_code"
    CODEX = "codex"


class EventCategory(str, Enum):
    PERMISSION = "permission"
    IDLE = "idle"
    DONE = "done"
    ERROR = "error"


@dataclass
class SessionInfo:
    session_id: str
    cwd: str
    project_name: str  # leaf directory from cwd, per D-04
    provider: Provider = Provider.CLAUDE_CODE


@dataclass
class NotifierEvent:
    category: EventCategory
    session: SessionInfo
    hook_event_name: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    raw_payload: Dict[str, Any] = field(default_factory=dict)
    message: Optional[str] = None
    provider: Provider = Provider.CLAUDE_CODE

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def classify_hook_event(
    raw: Dict[str, Any],
    event_type: str,
    provider: Union[Provider, str] = Provider.CLAUDE_CODE,
) -> NotifierEvent:
    """Classify a raw hook payload into a NotifierEvent.

    Per D-01: produces 4 categories (permission, idle, done, error).
    Per D-03: Notification events classified by notification_type field.
    Per critical research finding: No standalone Idle hook event --
      idle maps from Notification + idle_prompt.
    Provider drives provider-specific classification and propagates to
    SessionInfo and NotifierEvent.
    """
    from notifier.core.session import extract_session

    if isinstance(provider, str):
        try:
            provider = Provider(provider)
        except ValueError:
            provider = Provider.CLAUDE_CODE

    session = extract_session(raw, provider=provider)
    category, message = _classify(provider, event_type, raw)

    return NotifierEvent(
        category=category,
        session=session,
        hook_event_name=event_type,
        raw_payload=raw,
        message=message,
        provider=provider,
    )


def _classify(provider: Provider, event_type: str, raw: Dict[str, Any]):
    """Dispatch to provider-specific classification."""
    if provider == Provider.CODEX:
        return _classify_codex(event_type, raw)
    return _classify_claude_code(event_type, raw)


def _classify_claude_code(event_type: str, raw: Dict[str, Any]):
    """Claude Code classification rules.

    - Notification + permission_prompt -> PERMISSION (D-03)
    - Notification + idle_prompt -> IDLE (research: no standalone Idle event)
    - Stop -> DONE
    - SessionStart -> IDLE (session started, no notification action)
    - Unknown event_type -> ERROR
    - Notification with unhandled matcher -> ERROR (e.g., auth_success, elicitation)
    """
    if event_type == "Notification":
        ntype = raw.get("notification_type", "")
        if ntype == "permission_prompt":
            return EventCategory.PERMISSION, raw.get("message")
        elif ntype == "idle_prompt":
            return EventCategory.IDLE, raw.get("message")
        else:
            return EventCategory.ERROR, f"Unhandled notification type: {ntype}"

    if event_type == "Stop":
        return EventCategory.DONE, (raw.get("last_assistant_message") or "")[:200]

    if event_type == "SessionStart":
        return EventCategory.IDLE, "Session started"

    return EventCategory.ERROR, f"Unknown event type: {event_type}"


def _classify_codex(event_type: str, raw: Dict[str, Any]):
    """Codex classification rules.

    Per D-06: PermissionRequest -> PERMISSION.
    Per D-07: Stop -> DONE.
    Per D-08: SessionStart -> IDLE (session update only).
    Per D-10: Unknown Codex events -> ERROR.
    """
    if event_type == "PermissionRequest":
        # Prefer message, then tool_name, then fallback
        msg = raw.get("message") or raw.get("tool_name") or "Codex needs permission"
        return EventCategory.PERMISSION, msg

    if event_type == "Stop":
        # Prefer final_response, then last_assistant_message, then fallback
        msg = (raw.get("final_response") or raw.get("last_assistant_message") or "Codex task complete")
        return EventCategory.DONE, msg

    if event_type == "SessionStart":
        return EventCategory.IDLE, "Session started"

    return EventCategory.ERROR, f"Unknown Codex event type: {event_type}"

"""Tests for event classification (covers HOOK-03 classification behavior)."""
import pytest
from notifier.core.events import EventCategory, SessionInfo, NotifierEvent, classify_hook_event


class TestEventCategory:
    """D-01: Verify all 4 categories exist."""

    def test_has_permission(self):
        assert EventCategory.PERMISSION.value == "permission"

    def test_has_idle(self):
        assert EventCategory.IDLE.value == "idle"

    def test_has_done(self):
        assert EventCategory.DONE.value == "done"

    def test_has_error(self):
        assert EventCategory.ERROR.value == "error"


class TestClassifyHookEvent:
    """D-03: Classification by event type and notification_type field."""

    def test_notification_permission_prompt(self):
        """Notification + permission_prompt -> PERMISSION."""
        raw = {"notification_type": "permission_prompt", "session_id": "s1", "cwd": "/t"}
        event = classify_hook_event(raw, "Notification")
        assert event.category == EventCategory.PERMISSION

    def test_notification_idle_prompt(self):
        """Notification + idle_prompt -> IDLE (no standalone Idle hook event)."""
        raw = {"notification_type": "idle_prompt", "session_id": "s1", "cwd": "/t"}
        event = classify_hook_event(raw, "Notification")
        assert event.category == EventCategory.IDLE

    def test_stop(self):
        """Stop -> DONE."""
        raw = {"session_id": "s1", "cwd": "/t", "stop_reason": "done"}
        event = classify_hook_event(raw, "Stop")
        assert event.category == EventCategory.DONE

    def test_session_start(self):
        """SessionStart -> IDLE (with 'Session started' message, no notification action)."""
        raw = {"session_id": "s1", "cwd": "/t", "start_reason": "new"}
        event = classify_hook_event(raw, "SessionStart")
        assert event.category == EventCategory.IDLE
        assert event.message == "Session started"

    def test_unknown_notification_type(self):
        """Notification + unhandled matcher -> ERROR."""
        raw = {"notification_type": "auth_success", "session_id": "s1", "cwd": "/t"}
        event = classify_hook_event(raw, "Notification")
        assert event.category == EventCategory.ERROR

    def test_unknown_event_type(self):
        """Unrecognized event type -> ERROR."""
        raw = {"session_id": "s1", "cwd": "/t"}
        event = classify_hook_event(raw, "UnknownEvent")
        assert event.category == EventCategory.ERROR

    def test_missing_session_id_defaults_to_unknown(self):
        """Missing session_id -> 'unknown'."""
        raw = {"cwd": "/t", "notification_type": "permission_prompt"}
        event = classify_hook_event(raw, "Notification")
        assert event.session.session_id == "unknown"

    def test_missing_cwd_defaults_unknown_project(self):
        """Missing/empty cwd -> project_name='unknown'."""
        raw = {"session_id": "s1", "cwd": ""}
        event = classify_hook_event(raw, "Stop")
        assert event.session.project_name == "unknown"

    def test_notifier_event_to_dict(self):
        """to_dict() produces serializable dict with all expected keys."""
        raw = {"notification_type": "permission_prompt", "session_id": "s1", "cwd": "/t"}
        event = classify_hook_event(raw, "Notification")
        d = event.to_dict()
        assert "category" in d
        assert "session" in d
        assert "hook_event_name" in d
        assert "timestamp" in d
        assert "raw_payload" in d
        assert d["hook_event_name"] == "Notification"

    def test_session_info_construction(self):
        """SessionInfo stores session_id, cwd, project_name."""
        si = SessionInfo(session_id="abc", cwd="/projects/my-app", project_name="my-app")
        assert si.session_id == "abc"
        assert si.cwd == "/projects/my-app"
        assert si.project_name == "my-app"

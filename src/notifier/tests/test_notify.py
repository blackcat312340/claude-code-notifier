"""Tests for notification dispatch (covers ATTN-01, ATTN-02, ATTN-03)."""
import pytest
import time
from unittest.mock import patch, MagicMock
from notifier.core.events import EventCategory, NotifierEvent, SessionInfo
from notifier.core.notify import (
    dispatch_notification,
    NOTIFY_COOLDOWN_S,
    NOTIFY_CATEGORIES,
    _check_cooldown,
    _build_body,
)


def _make_event(category, project_name="my-project", message=None):
    return NotifierEvent(
        category=category,
        session=SessionInfo(
            session_id="test-s1",
            cwd=f"/test/{project_name}",
            project_name=project_name,
        ),
        hook_event_name="Notification",
        message=message,
    )


class TestNotifyCategories:
    """D-05: Only PERMISSION, IDLE, DONE produce notifications."""

    def test_permission_in_notify_set(self):
        assert EventCategory.PERMISSION in NOTIFY_CATEGORIES

    def test_idle_in_notify_set(self):
        assert EventCategory.IDLE in NOTIFY_CATEGORIES

    def test_done_in_notify_set(self):
        assert EventCategory.DONE in NOTIFY_CATEGORIES

    def test_error_not_in_notify_set(self):
        assert EventCategory.ERROR not in NOTIFY_CATEGORIES


class TestBuildBody:
    """D-04: Notification body format per category."""

    def test_permission_body(self):
        event = _make_event(EventCategory.PERMISSION, message="Claude wants to run npm install")
        body = _build_body(event)
        assert "Permission needed" in body
        assert "Claude wants to run npm install" in body

    def test_permission_body_no_message(self):
        event = _make_event(EventCategory.PERMISSION, message=None)
        body = _build_body(event)
        assert "Permission needed" in body

    def test_idle_body(self):
        event = _make_event(EventCategory.IDLE, message="Awaiting instructions")
        body = _build_body(event)
        assert "Waiting for input" in body
        assert "Awaiting instructions" in body

    def test_idle_body_no_message(self):
        event = _make_event(EventCategory.IDLE, message=None)
        body = _build_body(event)
        assert "Waiting for input" in body

    def test_done_body(self):
        event = _make_event(EventCategory.DONE, message="Task complete")
        body = _build_body(event)
        assert "Task complete" in body

    def test_done_body_truncates_long_message(self):
        long_msg = "x" * 300
        event = _make_event(EventCategory.DONE, message=long_msg)
        body = _build_body(event)
        assert len(body) <= 220  # "Task complete — " + 200 chars


class TestCheckCooldown:
    """D-06: 30s cooldown per (project, category)."""

    def test_first_call_returns_true(self):
        from notifier.core.notify import _cooldowns
        _cooldowns.clear()
        assert _check_cooldown("proj-a", EventCategory.PERMISSION) is True

    def test_second_call_within_cooldown_returns_false(self):
        from notifier.core.notify import _cooldowns
        _cooldowns.clear()
        _check_cooldown("proj-b", EventCategory.IDLE)
        assert _check_cooldown("proj-b", EventCategory.IDLE) is False

    def test_different_project_allowed(self):
        from notifier.core.notify import _cooldowns
        _cooldowns.clear()
        _check_cooldown("proj-a", EventCategory.PERMISSION)
        assert _check_cooldown("proj-b", EventCategory.PERMISSION) is True

    def test_different_category_same_project_allowed(self):
        from notifier.core.notify import _cooldowns
        _cooldowns.clear()
        _check_cooldown("proj-a", EventCategory.PERMISSION)
        assert _check_cooldown("proj-a", EventCategory.IDLE) is True

    def test_cooldown_uses_period(self):
        """Verify NOTIFY_COOLDOWN_S is the period used."""
        assert NOTIFY_COOLDOWN_S == 30


class TestDispatchNotification:
    """Integration: dispatch_notification with winotify mock."""

    def test_error_event_returns_false(self):
        event = _make_event(EventCategory.ERROR)
        result = dispatch_notification(event)
        assert result is False

    @patch("notifier.core.notify.Notification")
    def test_permission_event_sends_notification(self, mock_notify_cls):
        from notifier.core.notify import _cooldowns
        _cooldowns.clear()
        mock_notify = MagicMock()
        mock_notify_cls.return_value = mock_notify

        event = _make_event(
            EventCategory.PERMISSION,
            project_name="my-project",
            message="Claude wants to run npm install",
        )
        result = dispatch_notification(event)

        assert result is True
        mock_notify_cls.assert_called_once()
        call_kwargs = mock_notify_cls.call_args.kwargs
        assert call_kwargs["title"] == "my-project"
        assert "Permission needed" in call_kwargs["msg"]
        assert call_kwargs["app_id"] == "Claude Code Notifier"
        mock_notify.show.assert_called_once()

    @patch("notifier.core.notify.Notification")
    def test_cooldown_suppresses_second_notification(self, mock_notify_cls):
        from notifier.core.notify import _cooldowns
        _cooldowns.clear()
        mock_notify = MagicMock()
        mock_notify_cls.return_value = mock_notify

        event = _make_event(EventCategory.DONE, project_name="p1")
        dispatch_notification(event)
        result2 = dispatch_notification(event)

        assert result2 is False
        # Only one notification created
        assert mock_notify_cls.call_count == 1

    @patch("notifier.core.notify.Notification")
    def test_different_projects_both_notify(self, mock_notify_cls):
        from notifier.core.notify import _cooldowns
        _cooldowns.clear()
        mock_notify = MagicMock()
        mock_notify_cls.return_value = mock_notify

        dispatch_notification(_make_event(EventCategory.IDLE, project_name="alpha"))
        dispatch_notification(_make_event(EventCategory.IDLE, project_name="beta"))

        assert mock_notify_cls.call_count == 2

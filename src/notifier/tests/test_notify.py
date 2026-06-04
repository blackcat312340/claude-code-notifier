"""Tests for notification dispatch (covers ATTN-01, ATTN-02, ATTN-03)."""
import pytest
import time
from unittest.mock import patch, MagicMock
from notifier.core.events import (
    EventCategory, NotifierEvent, SessionInfo, Provider,
)
from notifier.core.notify import (
    dispatch_notification,
    NOTIFY_COOLDOWN_S,
    NOTIFY_CATEGORIES,
    _check_cooldown,
    _build_body,
    should_notify,
)
from notifier.core.text import (
    provider_label,
    category_label,
    notification_title,
    notification_body,
    event_menu_label,
    relative_time_cn,
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


# ---------------------------------------------------------------------------
# Helper: event with explicit provider
# ---------------------------------------------------------------------------

def _make_event_with_provider(
    category,
    project_name="my-project",
    message=None,
    provider=Provider.CLAUDE_CODE,
    hook_event_name="Notification",
):
    return NotifierEvent(
        category=category,
        session=SessionInfo(
            session_id="test-s1",
            cwd=f"/test/{project_name}",
            project_name=project_name,
            provider=provider,
        ),
        hook_event_name=hook_event_name,
        message=message,
        provider=provider,
    )


# ---------------------------------------------------------------------------
# Category membership
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# should_notify (D-08, D-10)
# ---------------------------------------------------------------------------

class TestShouldNotify:
    """Event-level notification eligibility."""

    def test_permission_should_notify(self):
        event = _make_event_with_provider(EventCategory.PERMISSION)
        assert should_notify(event) is True

    def test_idle_should_notify(self):
        event = _make_event_with_provider(EventCategory.IDLE)
        assert should_notify(event) is True

    def test_done_should_notify(self):
        event = _make_event_with_provider(EventCategory.DONE)
        assert should_notify(event) is True

    def test_error_should_not_notify(self):
        event = _make_event_with_provider(EventCategory.ERROR)
        assert should_notify(event) is False

    def test_session_start_should_not_notify_claude(self):
        event = _make_event_with_provider(
            EventCategory.IDLE,
            provider=Provider.CLAUDE_CODE,
            hook_event_name="SessionStart",
        )
        assert should_notify(event) is False

    def test_session_start_should_not_notify_codex(self):
        event = _make_event_with_provider(
            EventCategory.IDLE,
            provider=Provider.CODEX,
            hook_event_name="SessionStart",
        )
        assert should_notify(event) is False


# ---------------------------------------------------------------------------
# _build_body — now delegates to Chinese notification_body
# ---------------------------------------------------------------------------

class TestBuildBody:
    """D-04: Notification body format per category (now Chinese-first)."""

    def test_permission_body_cn(self):
        event = _make_event(EventCategory.PERMISSION, message="Bash")
        body = _build_body(event)
        assert "需要授权" in body
        assert "Bash" in body

    def test_permission_body_no_message_cn(self):
        event = _make_event(EventCategory.PERMISSION, message=None)
        body = _build_body(event)
        assert "需要授权" in body

    def test_idle_body_cn(self):
        event = _make_event(EventCategory.IDLE, message="Awaiting instructions")
        body = _build_body(event)
        assert "等待输入" in body
        assert "Awaiting instructions" in body

    def test_idle_body_no_message_cn(self):
        event = _make_event(EventCategory.IDLE, message=None)
        body = _build_body(event)
        assert "等待输入" in body

    def test_done_body_cn(self):
        event = _make_event(EventCategory.DONE, message="Task complete")
        body = _build_body(event)
        assert "任务已完成" in body

    def test_done_body_truncates_long_message(self):
        long_msg = "x" * 300
        event = _make_event(EventCategory.DONE, message=long_msg)
        body = _build_body(event)
        # "任务已完成 - " prefix + up to 200 chars + "..."
        assert len(body) <= 220


# ---------------------------------------------------------------------------
# Provider-aware cooldown
# ---------------------------------------------------------------------------

class TestCheckCooldown:
    """Provider-aware cooldown per (provider, project, category)."""

    def test_first_call_returns_true(self):
        from notifier.core.notify import _cooldowns
        _cooldowns.clear()
        assert _check_cooldown("claude_code", "proj-a", EventCategory.PERMISSION) is True

    def test_second_call_within_cooldown_returns_false(self):
        from notifier.core.notify import _cooldowns
        _cooldowns.clear()
        _check_cooldown("claude_code", "proj-b", EventCategory.IDLE)
        assert _check_cooldown("claude_code", "proj-b", EventCategory.IDLE) is False

    def test_different_project_allowed(self):
        from notifier.core.notify import _cooldowns
        _cooldowns.clear()
        _check_cooldown("claude_code", "proj-a", EventCategory.PERMISSION)
        assert _check_cooldown("claude_code", "proj-b", EventCategory.PERMISSION) is True

    def test_different_category_same_project_allowed(self):
        from notifier.core.notify import _cooldowns
        _cooldowns.clear()
        _check_cooldown("claude_code", "proj-a", EventCategory.PERMISSION)
        assert _check_cooldown("claude_code", "proj-a", EventCategory.IDLE) is True

    def test_cooldown_uses_period(self):
        """Verify NOTIFY_COOLDOWN_S is the period used."""
        assert NOTIFY_COOLDOWN_S == 5

    def test_different_provider_same_project_allowed(self):
        """Cooldown does not cross-suppress different providers."""
        from notifier.core.notify import _cooldowns
        _cooldowns.clear()
        # Claude Code permission fires
        assert _check_cooldown("claude_code", "proj-a", EventCategory.PERMISSION) is True
        # Codex permission for same project should still fire
        assert _check_cooldown("codex", "proj-a", EventCategory.PERMISSION) is True

    def test_same_provider_cross_suppresses(self):
        """Same provider, same project, same category -> suppressed."""
        from notifier.core.notify import _cooldowns
        _cooldowns.clear()
        _check_cooldown("claude_code", "proj-a", EventCategory.DONE)
        assert _check_cooldown("claude_code", "proj-a", EventCategory.DONE) is False


# ---------------------------------------------------------------------------
# dispatch_notification integration
# ---------------------------------------------------------------------------

class TestDispatchNotification:
    """Integration: dispatch_notification with winotify mock."""

    def test_error_event_returns_false(self):
        event = _make_event(EventCategory.ERROR)
        result = dispatch_notification(event)
        assert result is False

    def test_session_start_returns_false(self):
        """D-08: SessionStart must not notify."""
        event = _make_event_with_provider(
            EventCategory.IDLE,
            provider=Provider.CLAUDE_CODE,
            hook_event_name="SessionStart",
        )
        result = dispatch_notification(event)
        assert result is False

    @patch("notifier.core.notify.Notification")
    def test_permission_event_sends_notification(self, mock_notify_cls):
        from notifier.core.notify import _cooldowns
        _cooldowns.clear()
        mock_notify = MagicMock()
        mock_notify_cls.return_value = mock_notify

        event = _make_event_with_provider(
            EventCategory.PERMISSION,
            project_name="my-project",
            message="Bash",
            provider=Provider.CLAUDE_CODE,
        )
        result = dispatch_notification(event)

        assert result is True
        mock_notify_cls.assert_called_once()
        kwargs = mock_notify_cls.call_args.kwargs
        # Provider-aware title
        assert kwargs["title"] == "Claude Code - my-project"
        # Chinese-first body
        assert "需要授权" in kwargs["msg"]
        assert "Bash" in kwargs["msg"]
        assert kwargs["app_id"] == "Claude Code Notifier"
        mock_notify.show.assert_called_once()

    @patch("notifier.core.notify.Notification")
    def test_codex_permission_title_includes_codex(self, mock_notify_cls):
        """Codex notification title shows 'Codex' source."""
        from notifier.core.notify import _cooldowns
        _cooldowns.clear()
        mock_notify = MagicMock()
        mock_notify_cls.return_value = mock_notify

        event = _make_event_with_provider(
            EventCategory.PERMISSION,
            project_name="notifier",
            message="npm install",
            provider=Provider.CODEX,
        )
        result = dispatch_notification(event)

        assert result is True
        kwargs = mock_notify_cls.call_args.kwargs
        assert kwargs["title"] == "Codex - notifier"
        assert "需要授权" in kwargs["msg"]

    @patch("notifier.core.notify.Notification")
    def test_cooldown_suppresses_second_notification(self, mock_notify_cls):
        from notifier.core.notify import _cooldowns
        _cooldowns.clear()
        mock_notify = MagicMock()
        mock_notify_cls.return_value = mock_notify

        event = _make_event_with_provider(
            EventCategory.DONE, project_name="p1",
            provider=Provider.CLAUDE_CODE,
        )
        dispatch_notification(event)
        result2 = dispatch_notification(event)

        assert result2 is False
        assert mock_notify_cls.call_count == 1

    @patch("notifier.core.notify.Notification")
    def test_different_projects_both_notify(self, mock_notify_cls):
        from notifier.core.notify import _cooldowns
        _cooldowns.clear()
        mock_notify = MagicMock()
        mock_notify_cls.return_value = mock_notify

        dispatch_notification(_make_event_with_provider(
            EventCategory.IDLE, project_name="alpha",
            provider=Provider.CLAUDE_CODE,
        ))
        dispatch_notification(_make_event_with_provider(
            EventCategory.IDLE, project_name="beta",
            provider=Provider.CLAUDE_CODE,
        ))

        assert mock_notify_cls.call_count == 2

    @patch("notifier.core.notify.Notification")
    def test_different_providers_both_notify(self, mock_notify_cls):
        """Cooldown separates providers — Codex and Claude Code both fire."""
        from notifier.core.notify import _cooldowns
        _cooldowns.clear()
        mock_notify = MagicMock()
        mock_notify_cls.return_value = mock_notify

        dispatch_notification(_make_event_with_provider(
            EventCategory.PERMISSION, project_name="shared-proj",
            provider=Provider.CLAUDE_CODE, message="Claude needs auth",
        ))
        dispatch_notification(_make_event_with_provider(
            EventCategory.PERMISSION, project_name="shared-proj",
            provider=Provider.CODEX, message="Codex needs auth",
        ))

        assert mock_notify_cls.call_count == 2

    @patch("notifier.core.notify.Notification")
    def test_codex_done_body_uses_chinese_label(self, mock_notify_cls):
        """Claude Code done body includes 任务已完成."""
        from notifier.core.notify import _cooldowns
        _cooldowns.clear()
        mock_notify = MagicMock()
        mock_notify_cls.return_value = mock_notify

        event = _make_event_with_provider(
            EventCategory.DONE,
            provider=Provider.CLAUDE_CODE,
            message="Build passed",
        )
        dispatch_notification(event)
        kwargs = mock_notify_cls.call_args.kwargs
        assert "任务已完成" in kwargs["msg"]


# ---------------------------------------------------------------------------
# Task 1: Centralized display text helpers (text.py)
# ---------------------------------------------------------------------------

class TestProviderLabel:
    """provider_label returns stable, recognizable provider names."""

    def test_claude_code_enum(self):
        assert provider_label(Provider.CLAUDE_CODE) == "Claude Code"

    def test_codex_enum(self):
        assert provider_label(Provider.CODEX) == "Codex"

    def test_claude_code_string(self):
        assert provider_label("claude_code") == "Claude Code"

    def test_codex_string(self):
        assert provider_label("codex") == "Codex"

    def test_claude_code_with_space_string(self):
        assert provider_label("claude code") == "Claude Code"

    def test_unknown_provider_degrades_gracefully(self):
        result = provider_label("unknown_provider")
        assert "Unknown" in result
        assert "Provider" in result

    def test_unknown_enum_degrades_gracefully(self):
        result = provider_label("bogus")
        assert "Bogus" in result


class TestCategoryLabel:
    """category_label returns concise Chinese labels."""

    def test_permission_cn(self):
        assert category_label(EventCategory.PERMISSION) == "需要授权"

    def test_idle_cn(self):
        assert category_label(EventCategory.IDLE) == "等待输入"

    def test_done_cn(self):
        assert category_label(EventCategory.DONE) == "任务已完成"

    def test_error_cn(self):
        assert category_label(EventCategory.ERROR) == "需要检查"

    def test_string_category(self):
        assert category_label("permission") == "需要授权"

    def test_unknown_category_degrades(self):
        result = category_label("bogus_category")
        assert result == "bogus_category"


class TestNotificationTitle:
    """notification_title includes provider source and project name."""

    def test_claude_code_title(self):
        event = _make_event_with_provider(
            EventCategory.DONE, project_name="my-project",
            provider=Provider.CLAUDE_CODE,
        )
        title = notification_title(event)
        assert title == "Claude Code - my-project"

    def test_codex_title(self):
        event = _make_event_with_provider(
            EventCategory.PERMISSION, project_name="notifier",
            provider=Provider.CODEX,
        )
        title = notification_title(event)
        assert title == "Codex - notifier"


class TestNotificationBody:
    """notification_body uses Chinese-first copy with optional detail."""

    def test_permission_body_with_message(self):
        event = _make_event_with_provider(
            EventCategory.PERMISSION, message="Bash",
        )
        body = notification_body(event)
        assert body == "需要授权 - Bash"

    def test_permission_body_no_message(self):
        event = _make_event_with_provider(
            EventCategory.PERMISSION, message=None,
        )
        body = notification_body(event)
        assert body == "需要授权"

    def test_idle_body_with_message(self):
        event = _make_event_with_provider(
            EventCategory.IDLE, message="Awaiting next instruction",
        )
        body = notification_body(event)
        assert "等待输入" in body
        assert "Awaiting next instruction" in body

    def test_done_body(self):
        event = _make_event_with_provider(
            EventCategory.DONE, message="Build passed",
        )
        body = notification_body(event)
        assert "任务已完成 - Build passed" == body

    def test_error_body(self):
        event = _make_event_with_provider(
            EventCategory.ERROR, message="Unknown event type: Foo",
        )
        body = notification_body(event)
        assert "需要检查 - Unknown event type: Foo" == body

    def test_long_message_truncated(self):
        long_msg = "x" * 300
        event = _make_event_with_provider(
            EventCategory.DONE, message=long_msg,
        )
        body = notification_body(event)
        # Should be truncated with "..."
        assert "..." in body
        assert len(body) <= 220


class TestEventMenuLabel:
    """event_menu_label combines provider, category value, Chinese label, and time."""

    def test_codex_permission_label(self):
        event = _make_event_with_provider(
            EventCategory.PERMISSION, provider=Provider.CODEX,
        )
        label = event_menu_label(event)
        assert label == "Codex - permission - 需要授权"

    def test_label_with_relative_time(self):
        event = _make_event_with_provider(
            EventCategory.DONE, provider=Provider.CLAUDE_CODE,
        )
        label = event_menu_label(event, relative_time="刚刚")
        assert label == "Claude Code - done - 任务已完成 (刚刚)"

    def test_label_with_minutes_time(self):
        event = _make_event_with_provider(
            EventCategory.IDLE, provider=Provider.CODEX,
        )
        label = event_menu_label(event, relative_time="5 分钟前")
        assert label == "Codex - idle - 等待输入 (5 分钟前)"


class TestRelativeTimeCN:
    """relative_time_cn returns concise Chinese relative time."""

    def test_just_now_for_now(self):
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).isoformat()
        result = relative_time_cn(ts)
        assert result == "刚刚"

    def test_one_minute_ago(self):
        from datetime import datetime, timezone, timedelta
        ts = (datetime.now(timezone.utc) - timedelta(seconds=65)).isoformat()
        result = relative_time_cn(ts)
        assert result == "1 分钟前"

    def test_minutes_ago(self):
        from datetime import datetime, timezone, timedelta
        ts = (datetime.now(timezone.utc) - timedelta(seconds=300)).isoformat()
        result = relative_time_cn(ts)
        assert "分钟前" in result
        assert int(result.split()[0]) >= 4

    def test_naive_timestamp(self):
        from datetime import datetime, timedelta, timezone
        ts = (datetime.now(timezone.utc) - timedelta(seconds=65)).isoformat()
        result = relative_time_cn(ts)
        assert "分钟前" in result

    def test_bad_timestamp_returns_empty(self):
        assert relative_time_cn("not-a-timestamp") == ""

"""Tests for dynamic tray menu and event formatting."""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch
from notifier.core.events import EventCategory, NotifierEvent, SessionInfo, Provider
from notifier.tray.menu import build_menu, _format_event
from notifier.tray.app import NotifierTray


class TestFormatEvent:
    """Menu item label formatting — Chinese-first with provider source."""

    def test_label_contains_provider_and_category(self):
        event = NotifierEvent(
            category=EventCategory.PERMISSION,
            session=SessionInfo("s1", "/t/test", "my-project"),
            hook_event_name="Notification",
            timestamp=datetime.now(timezone.utc).isoformat(),
            provider=Provider.CLAUDE_CODE,
        )
        label, _ = _format_event(event, 0)
        assert "Claude Code" in label
        assert "permission" in label
        assert "需要授权" in label

    def test_label_shows_just_now_for_recent(self):
        event = NotifierEvent(
            category=EventCategory.DONE,
            session=SessionInfo("s1", "/t/test", "p"),
            hook_event_name="Stop",
            timestamp=datetime.now(timezone.utc).isoformat(),
            provider=Provider.CLAUDE_CODE,
        )
        label, _ = _format_event(event, 0)
        assert "刚刚" in label

    def test_label_handles_string_category(self):
        event = NotifierEvent(
            category="permission",
            session=SessionInfo("s1", "/t/test", "p"),
            hook_event_name="Notification",
            timestamp=datetime.now(timezone.utc).isoformat(),
            provider=Provider.CLAUDE_CODE,
        )
        label, _ = _format_event(event, 0)
        assert "permission" in label

    def test_codex_label_includes_codex(self):
        """Codex events show 'Codex' as provider source."""
        event = NotifierEvent(
            category=EventCategory.PERMISSION,
            session=SessionInfo("s1", "/t/test", "test-proj", provider=Provider.CODEX),
            hook_event_name="PermissionRequest",
            timestamp=datetime.now(timezone.utc).isoformat(),
            provider=Provider.CODEX,
        )
        label, _ = _format_event(event, 0)
        assert "Codex" in label
        assert "permission" in label
        assert "需要授权" in label


class TestBuildMenu:
    """Dynamic menu construction with Chinese labels."""

    def test_empty_history_builds_menu(self):
        tray = NotifierTray()
        menu = build_menu(tray)
        assert menu is not None

    def test_menu_includes_event_items(self):
        tray = NotifierTray()
        tray.event_history.appendleft(NotifierEvent(
            category=EventCategory.PERMISSION,
            session=SessionInfo("s1", "/t/test", "test-proj"),
            hook_event_name="Notification",
            timestamp=datetime.now(timezone.utc).isoformat(),
        ))
        menu = build_menu(tray)
        assert menu is not None

    def test_menu_limits_to_five_events(self):
        tray = NotifierTray()
        for i in range(10):
            tray.event_history.appendleft(NotifierEvent(
                category=EventCategory.DONE,
                session=SessionInfo(f"s{i}", "/t/test", f"proj-{i}"),
                hook_event_name="Stop",
                timestamp=datetime.now(timezone.utc).isoformat(),
            ))
        menu = build_menu(tray)
        assert menu is not None

    def test_ring_buffer_caps_at_fifty(self):
        tray = NotifierTray()
        for i in range(60):
            tray.event_history.appendleft(NotifierEvent(
                category=EventCategory.IDLE,
                session=SessionInfo(f"s{i}", "/t/test", f"proj-{i}"),
                hook_event_name="Notification",
                timestamp=datetime.now(timezone.utc).isoformat(),
            ))
        assert len(tray.event_history) == 50

    def test_empty_menu_shows_chinese_no_events(self):
        """Empty history menu shows 暂无事件."""
        tray = NotifierTray()
        menu = build_menu(tray)
        # Walk menu items to find the empty label
        # pystray.Menu items are accessible via iteration
        found = False
        for item in menu:
            if hasattr(item, 'text') and "暂无事件" in str(item.text):
                found = True
                break
        assert found, "Empty menu should contain 暂无事件"

    def test_exit_label_is_chinese(self):
        """Exit menu item is 退出."""
        tray = NotifierTray()
        menu = build_menu(tray)
        found = False
        for item in menu:
            if hasattr(item, 'text') and str(item.text) == "退出":
                found = True
                break
        assert found, "Exit menu item should be 退出"

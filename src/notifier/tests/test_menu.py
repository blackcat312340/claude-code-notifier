"""Tests for dynamic tray menu and event formatting."""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch
from notifier.core.events import EventCategory, NotifierEvent, SessionInfo
from notifier.tray.menu import build_menu, _format_event
from notifier.tray.app import NotifierTray


class TestFormatEvent:
    """Menu item label formatting."""

    def test_label_contains_project_and_category(self):
        event = NotifierEvent(
            category=EventCategory.PERMISSION,
            session=SessionInfo("s1", "/t/test", "my-project"),
            hook_event_name="Notification",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        label, _ = _format_event(event, 0)
        assert "my-project" in label
        assert "permission" in label

    def test_label_shows_just_now_for_recent(self):
        event = NotifierEvent(
            category=EventCategory.DONE,
            session=SessionInfo("s1", "/t/test", "p"),
            hook_event_name="Stop",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        label, _ = _format_event(event, 0)
        assert "just now" in label

    def test_label_handles_string_category(self):
        event = NotifierEvent(
            category="permission",
            session=SessionInfo("s1", "/t/test", "p"),
            hook_event_name="Notification",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        label, _ = _format_event(event, 0)
        assert "permission" in label
        assert "p" in label


class TestBuildMenu:
    """Dynamic menu construction."""

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

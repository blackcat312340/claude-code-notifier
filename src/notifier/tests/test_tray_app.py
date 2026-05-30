"""Tests for tray application (covers TRAY-01)."""
import pytest
import threading
from unittest.mock import patch
from notifier.tray.app import (
    NotifierTray,
    _make_icon_image,
    main,
)
from notifier.server.tcp_server import NotifierServer


class TestMakeIconImage:
    """D-03: Minimal placeholder tray icon."""

    def test_returns_64x64_image(self):
        img = _make_icon_image()
        assert img.size == (64, 64)

    def test_returns_rgba_mode(self):
        img = _make_icon_image()
        assert img.mode == "RGBA"


class TestNotifierTray:
    """D-08 through D-13: Tray application behavior."""

    def test_creates_with_server(self):
        tray = NotifierTray()
        assert isinstance(tray.server, NotifierServer)

    def test_server_thread_is_none_before_run(self):
        tray = NotifierTray()
        assert tray._server_thread is None

    def test_patch_injects_notification_hook(self):
        tray = NotifierTray()
        original = tray.server._update_session
        tray._patch_server_handler()
        assert tray.server._update_session is not original

    def test_tooltip_contains_app_name(self):
        tray = NotifierTray()
        text = tray._tooltip_text()
        assert "Claude Code Notifier" in text

    def test_tooltip_shows_zero_sessions(self):
        tray = NotifierTray()
        text = tray._tooltip_text()
        assert "0" in text or "Monitoring" in text

    def test_tooltip_shows_session_count(self):
        tray = NotifierTray()
        from notifier.server.tcp_server import SessionRecord
        tray.server.session_registry["s1||/test/p"] = SessionRecord(
            session_id="s1", cwd="/test/p", project_name="p",
            first_seen="2026-01-01T00:00:00", last_seen="2026-01-01T00:00:00",
        )
        text = tray._tooltip_text()
        assert "1" in text

    def test_build_menu_exists(self):
        tray = NotifierTray()
        menu = tray._build_menu()
        assert menu is not None

    def test_patched_handler_enqueues_events(self):
        """Verify the patched _update_session puts events on the notify queue."""
        tray = NotifierTray()
        tray._patch_server_handler()

        from notifier.core.events import EventCategory, NotifierEvent, SessionInfo
        event = NotifierEvent(
            category=EventCategory.PERMISSION,
            session=SessionInfo("s1", "/t/test", "test"),
            hook_event_name="Notification",
        )
        tray.server._update_session(event)
        # Event should be on the queue
        assert tray._notify_queue.qsize() == 1
        queued = tray._notify_queue.get_nowait()
        assert queued is event

    def test_patched_handler_updates_tooltip(self):
        """Verify the patched handler updates tray tooltip title."""
        tray = NotifierTray()
        tray._patch_server_handler()
        # Simulate having an icon
        from unittest.mock import MagicMock
        tray._icon = MagicMock()

        from notifier.core.events import EventCategory, NotifierEvent, SessionInfo
        from notifier.server.tcp_server import SessionRecord
        event = NotifierEvent(
            category=EventCategory.PERMISSION,
            session=SessionInfo("s1", "/t/test", "test"),
            hook_event_name="Notification",
        )
        tray.server._update_session(event)
        # Tooltip should be updated with session count
        assert tray._icon.title is not None
        assert "1" in tray._icon.title
        assert "Monitoring" in tray._icon.title

    def test_event_history_initialized(self):
        tray = NotifierTray()
        assert hasattr(tray, 'event_history')
        assert tray.event_history.maxlen == 50
        assert len(tray.event_history) == 0

    def test_patched_handler_records_history(self):
        tray = NotifierTray()
        tray._patch_server_handler()

        from notifier.core.events import EventCategory, NotifierEvent, SessionInfo
        event = NotifierEvent(
            category=EventCategory.PERMISSION,
            session=SessionInfo("s1", "/t/test", "test"),
            hook_event_name="Notification",
        )
        tray.server._update_session(event)
        assert len(tray.event_history) == 1
        assert tray.event_history[0] is event

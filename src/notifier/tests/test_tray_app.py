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

    def test_returns_rgb_mode(self):
        img = _make_icon_image()
        assert img.mode == "RGB"


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

    def test_create_menu_exists(self):
        tray = NotifierTray()
        menu = tray._create_menu()
        assert menu is not None

    def test_patched_handler_dispatches_notifications(self):
        """Verify the patched _update_session calls dispatch_notification."""
        tray = NotifierTray()
        tray._patch_server_handler()

        with patch("notifier.tray.app.dispatch_notification") as mock_dispatch:
            from notifier.core.events import EventCategory, NotifierEvent, SessionInfo
            event = NotifierEvent(
                category=EventCategory.PERMISSION,
                session=SessionInfo("s1", "/t/test", "test"),
                hook_event_name="Notification",
            )
            tray.server._update_session(event)
            mock_dispatch.assert_called_once_with(event)

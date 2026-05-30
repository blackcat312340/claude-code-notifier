import logging
import threading
import asyncio
from PIL import Image, ImageDraw
from notifier.core.notify import dispatch_notification
from notifier.server.tcp_server import NotifierServer, HOST, PORT


# Simple 64x64 tray icon — blue square with white "N" (D-03: minimal placeholder)
def _make_icon_image():
    img = Image.new("RGB", (64, 64), color=(59, 130, 246))
    draw = ImageDraw.Draw(img)
    draw.text((18, 8), "N", fill=(255, 255, 255))
    return img


class NotifierTray:
    """Tray application that runs the TCP server in a daemon thread.

    Per D-09: TCP server runs in daemon thread, pystray owns main thread.
    Per D-10: No console window — use pythonw.exe or .pyw launcher.
    Per D-12: Right-click menu has single "Exit" item.
    Per D-13: Tooltip shows "Claude Code Notifier — Monitoring (N sessions)".
    """

    def __init__(self):
        self.server = NotifierServer()
        self._server_thread = None
        self._loop = None

    def _patch_server_handler(self):
        """Monkey-patch _update_session to inject notification dispatch.

        After the existing session registry update, we dispatch a notification
        for attention-worthy events. This keeps the TCP server code unchanged
        while adding notification behavior.
        """
        original_update = self.server._update_session

        def patched_update(event):
            original_update(event)
            # Dispatch notification after session update
            dispatch_notification(event)

        self.server._update_session = patched_update

    def _run_tcp_server(self):
        """Run the asyncio TCP server in a daemon thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        try:
            loop.run_until_complete(self.server.serve())
        except Exception as exc:
            logging.error("TCP server error: %s", exc)

    def _tooltip_text(self):
        """Build tooltip text with live session count (D-13)."""
        count = len(self.server.session_registry)
        session_word = "session" if count == 1 else "sessions"
        return f"Claude Code Notifier - Monitoring ({count} {session_word})"

    def _create_menu(self):
        """Create the tray menu (D-12: Exit only)."""
        import pystray
        return pystray.Menu(
            pystray.MenuItem(
                "Exit",
                lambda icon, item: self.shutdown(icon),
            )
        )

    def shutdown(self, icon):
        """Stop the TCP server and quit the tray."""
        icon.stop()
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        logging.info("Notifier tray shutting down")

    def run(self):
        """Start the tray application (D-08: main entry via python -m notifier).

        Per D-09: TCP server starts in daemon thread before pystray.run()
        blocks the main thread. This ensures events are being received while
        the tray icon is visible.
        """
        import pystray

        self._patch_server_handler()

        # Start TCP server in daemon thread
        self._server_thread = threading.Thread(
            target=self._run_tcp_server,
            daemon=True,
            name="notifier-tcp-server",
        )
        self._server_thread.start()

        # Run pystray on main thread
        icon = pystray.Icon(
            name="Claude Code Notifier",
            icon=_make_icon_image(),
            title=self._tooltip_text(),
            menu=self._create_menu(),
        )
        icon.run()

        # Cleanup after icon.run() returns (user clicked Exit)
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)


def main():
    """Entry point for python -m notifier."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logging.info("Starting Claude Code Notifier tray...")
    tray = NotifierTray()
    tray.run()

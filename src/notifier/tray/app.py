import logging
import queue
import threading
import asyncio
from PIL import Image, ImageDraw
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
    Per D-13: Tooltip shows live session count, updated on each event.
    """

    def __init__(self):
        self.server = NotifierServer()
        self._server_thread = None
        self._loop = None
        self._icon = None
        self._notify_queue = queue.Queue()
        self._notify_worker = None

    def _patch_server_handler(self):
        """Hook _update_session to enqueue notifications and refresh tooltip."""
        original_update = self.server._update_session
        notify_queue = self._notify_queue

        def patched_update(event):
            original_update(event)
            notify_queue.put(event)
            # Refresh tray tooltip with new session count
            if self._icon:
                count = len(self.server.session_registry)
                s = "sessions" if count != 1 else "session"
                self._icon.title = (
                    f"Claude Code Notifier - Monitoring ({count} {s})"
                )

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

    def _run_notify_worker(self):
        """Process notification queue in a dedicated thread.

        Each event triggers a win10toast call. Running in its own thread
        avoids the daemon-thread WNDPROC issue and subprocess overhead.
        """
        from notifier.core.notify import dispatch_notification

        while True:
            event = self._notify_queue.get()
            if event is None:  # Shutdown signal
                break
            try:
                dispatch_notification(event)
            except Exception as exc:
                logging.warning("Notify worker error: %s", exc)

    def _tooltip_text(self):
        """Build initial tooltip text (D-13)."""
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
        """Stop the TCP server, notification worker, and quit the tray."""
        self._notify_queue.put(None)  # Signal worker to stop
        icon.stop()
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        logging.info("Notifier tray shutting down")

    def run(self):
        """Start the tray application (D-08: main entry via python -m notifier)."""
        import pystray

        # Start notification worker thread
        self._notify_worker = threading.Thread(
            target=self._run_notify_worker,
            daemon=True,
            name="notifier-notify-worker",
        )
        self._notify_worker.start()

        self._patch_server_handler()

        # Start TCP server in daemon thread
        self._server_thread = threading.Thread(
            target=self._run_tcp_server,
            daemon=True,
            name="notifier-tcp-server",
        )
        self._server_thread.start()

        # Run pystray on main thread
        self._icon = pystray.Icon(
            name="Claude Code Notifier",
            icon=_make_icon_image(),
            title=self._tooltip_text(),
            menu=self._create_menu(),
        )
        self._icon.run()

        # Cleanup after icon.run() returns (user clicked Exit)
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        self._notify_queue.put(None)


def main():
    """Entry point for python -m notifier."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logging.info("Starting Claude Code Notifier tray...")
    tray = NotifierTray()
    tray.run()

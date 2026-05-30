import logging
import queue
import threading
import asyncio
from collections import deque
from PIL import Image, ImageDraw
from notifier.server.tcp_server import NotifierServer, HOST, PORT


# Notification bell icon — yellow bell with red notification dot
def _make_icon_image():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Bell body (rounded rectangle)
    draw.rounded_rectangle([12, 6, 52, 42], radius=14, fill=(255, 215, 0))

    # Bell opening (arc at bottom + dark fill)
    draw.ellipse([18, 30, 46, 52], fill=(220, 185, 0))

    # Bell highlight (lighter arc near top)
    draw.ellipse([20, 10, 44, 24], fill=(255, 235, 80))

    # Clapper (small ball at bottom)
    draw.ellipse([27, 46, 37, 56], fill=(255, 215, 0))
    draw.ellipse([28, 47, 36, 55], fill=(255, 235, 100))

    # Red notification dot (top-right)
    draw.ellipse([42, 2, 56, 16], fill=(255, 50, 50))

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
        self.event_history = deque(maxlen=50)

    def _patch_server_handler(self):
        """Hook _update_session to enqueue notifications and refresh tooltip."""
        original_update = self.server._update_session
        notify_queue = self._notify_queue

        def patched_update(event):
            original_update(event)
            notify_queue.put(event)
            self.event_history.appendleft(event)
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

    def _build_menu(self):
        """Build dynamic tray menu (D-03, D-04)."""
        from notifier.tray.menu import build_menu
        return build_menu(self)

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

        # Run pystray on main thread (menu built dynamically per D-04)
        self._icon = pystray.Icon(
            name="Claude Code Notifier",
            icon=_make_icon_image(),
            title=self._tooltip_text(),
            menu=pystray.Menu(self._build_menu),
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

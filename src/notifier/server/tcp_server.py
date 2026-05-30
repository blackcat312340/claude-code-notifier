import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Any
from datetime import datetime, timezone
from notifier.core.events import NotifierEvent

HOST = "127.0.0.1"
PORT = 47921


@dataclass
class SessionRecord:
    """Tracks a Claude Code session in the registry.

    Per D-06: Created on first event from this session, stores timestamps.
    No expiry in Phase 1 -- lifecycle management deferred to Phase 4.
    """
    session_id: str
    cwd: str
    project_name: str
    first_seen: str
    last_seen: str


class NotifierServer:
    """Minimal TCP server receiving NDJSON events from the hook CLI.

    Per D-10: Listens on localhost TCP.
    Per D-12: Reads newline-delimited JSON (one event per line).

    Maintains a session_registry dict keyed by (session_id, cwd) composite key.
    """

    def __init__(self):
        self.session_registry: Dict[str, SessionRecord] = {}

    def _registry_key(self, session_id: str, cwd: str) -> str:
        """Generate composite key for session registry per D-05."""
        return f"{session_id}||{cwd}"

    def _update_session(self, event: NotifierEvent) -> None:
        """Add or update a session record in the registry."""
        key = self._registry_key(event.session.session_id, event.session.cwd)
        now = datetime.now(timezone.utc).isoformat()
        if key in self.session_registry:
            self.session_registry[key].last_seen = now
        else:
            self.session_registry[key] = SessionRecord(
                session_id=event.session.session_id,
                cwd=event.session.cwd,
                project_name=event.session.project_name,
                first_seen=now,
                last_seen=now,
            )

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """Handle one TCP connection from the hook CLI."""
        try:
            data = await asyncio.wait_for(reader.readline(), timeout=10.0)
            if data:
                payload = json.loads(data.decode().strip())
                # Reconstruct event from dict
                event = NotifierEvent(
                    category=payload.get("category", ""),
                    session=type("Session", (), {
                        "session_id": payload.get("session", {}).get("session_id", ""),
                        "cwd": payload.get("session", {}).get("cwd", ""),
                        "project_name": payload.get("session", {}).get("project_name", ""),
                    })(),
                    hook_event_name=payload.get("hook_event_name", ""),
                    timestamp=payload.get("timestamp", ""),
                    raw_payload=payload.get("raw_payload", {}),
                    message=payload.get("message"),
                )
                self._update_session(event)
                logging.info(
                    "Event received: %s | session=%s | project=%s",
                    event.hook_event_name,
                    event.session.session_id,
                    event.session.project_name,
                )
        except (asyncio.TimeoutError, json.JSONDecodeError, ConnectionError) as exc:
            logging.warning("TCP server handler error: %s", exc)
        finally:
            writer.close()
            await writer.wait_closed()

    async def serve(self):
        """Start the TCP server and run forever."""
        server = await asyncio.start_server(
            self._handle_client, host=HOST, port=PORT
        )
        addr = server.sockets[0].getsockname()
        logging.info("Notifier TCP server listening on %s:%s", addr[0], addr[1])
        async with server:
            await server.serve_forever()


def main():
    """Entry point for python -m notifier. Starts the TCP server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    server = NotifierServer()
    asyncio.run(server.serve())


if __name__ == "__main__":
    main()

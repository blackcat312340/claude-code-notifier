"""Tests for TCP IPC client (covers HOOK-03 forwarding behavior)."""
import pytest
import asyncio
import json
from notifier.core.events import EventCategory, NotifierEvent, SessionInfo
from notifier.core.ipc import send_event_or_drop


class TestSendEventOrDrop:
    """D-10/D-11: TCP send with retry and graceful failure."""

    def test_no_server_returns_gracefully(self):
        """Connection refused -> log warning, don't raise."""
        event = NotifierEvent(
            category=EventCategory.DONE,
            session=SessionInfo("s1", "/test", "test"),
            hook_event_name="Stop",
        )
        # No server is listening on this random high port
        send_event_or_drop(event, timeout=2, host="127.0.0.1", port=48765)

    @pytest.mark.asyncio
    async def test_sends_to_listening_server(self):
        """Event data arrives at listening TCP server."""
        received = []

        async def handler(reader, writer):
            data = await reader.readline()
            received.append(data)
            writer.close()
            await writer.wait_closed()

        # Use port 0 for OS-assigned available port
        server = await asyncio.start_server(handler, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]

        async with server:
            event = NotifierEvent(
                category=EventCategory.DONE,
                session=SessionInfo("s1", "/test", "test"),
                hook_event_name="Stop",
                message="Task complete",
            )
            send_event_or_drop(event, timeout=2, host="127.0.0.1", port=port)
            await asyncio.sleep(0.2)

        assert len(received) == 1
        parsed = json.loads(received[0].decode().strip())
        assert parsed["hook_event_name"] == "Stop"
        assert parsed["category"] == "done"
        assert parsed["session"]["session_id"] == "s1"

    @pytest.mark.asyncio
    async def test_sends_ndjson_format(self):
        """Wire format is NDJSON (one JSON line terminated by newline)."""
        received = bytearray()

        async def handler(reader, writer):
            chunk = await reader.read(4096)
            received.extend(chunk)
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(handler, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]

        async with server:
            event = NotifierEvent(
                category=EventCategory.IDLE,
                session=SessionInfo("s2", "/other", "other"),
                hook_event_name="SessionStart",
            )
            send_event_or_drop(event, timeout=2, host="127.0.0.1", port=port)
            await asyncio.sleep(0.2)

        text = received.decode()
        assert text.endswith("\n"), "NDJSON must end with newline"
        parsed = json.loads(text.strip())
        assert parsed["hook_event_name"] == "SessionStart"

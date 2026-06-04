"""Tests for the hook CLI event processing (covers HOOK-03 end-to-end)."""
import pytest
import asyncio
import json
from notifier.core.events import EventCategory, Provider
from notifier.cli.hook import process_hook_event


class TestProcessHookEvent:
    """Test the core logic of the hook CLI without stdin piping."""

    @pytest.mark.asyncio
    async def test_process_permission_event(self):
        """Notification+permission_prompt -> PERMISSION, forwarded via TCP."""
        received = []

        async def handler(reader, writer):
            data = await reader.readline()
            received.append(data)
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(handler, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]

        async with server:
            raw = {
                "session_id": "sess-001",
                "cwd": "/projects/my-app",
                "notification_type": "permission_prompt",
                "message": "Claude wants to run npm install",
            }
            process_hook_event(raw, "Notification", host="127.0.0.1", port=port)
            await asyncio.sleep(0.2)

        assert len(received) == 1
        parsed = json.loads(received[0].decode().strip())
        assert parsed["hook_event_name"] == "Notification"
        assert parsed["category"] == "permission"
        assert parsed["session"]["project_name"] == "my-app"

    @pytest.mark.asyncio
    async def test_process_stop_event(self):
        """Stop -> DONE, forwarded with correct metadata."""
        received = []

        async def handler(reader, writer):
            data = await reader.readline()
            received.append(data)
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(handler, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]

        async with server:
            raw = {
                "session_id": "sess-002",
                "cwd": "/projects/notifier",
                "stop_reason": "tool_use",
                "last_assistant_message": "I have completed the task",
            }
            process_hook_event(raw, "Stop", host="127.0.0.1", port=port)
            await asyncio.sleep(0.2)

        assert len(received) == 1
        parsed = json.loads(received[0].decode().strip())
        assert parsed["category"] == "done"
        assert parsed["session"]["project_name"] == "notifier"

    @pytest.mark.asyncio
    async def test_process_no_server_does_not_raise(self):
        """If no server is listening, process_hook_event drops gracefully."""
        raw = {
            "session_id": "sess-003",
            "cwd": "/projects/test",
            "notification_type": "idle_prompt",
        }
        # No server -> should log warning and return, not raise
        process_hook_event(raw, "Notification", host="127.0.0.1", port=48999, timeout=1)

    def test_process_without_server_returns_none(self):
        """send_event_or_drop returns None on failure (no exception)."""
        raw = {"session_id": "s1", "cwd": "/t", "notification_type": "permission_prompt"}
        # Should not raise any exception
        result = process_hook_event(raw, "Notification", host="127.0.0.1", port=48998, timeout=1)
        assert result is None

    @pytest.mark.asyncio
    async def test_process_codex_permission_request(self):
        """Codex PermissionRequest -> PERMISSION, forwarded with provider=codex."""
        received = []

        async def handler(reader, writer):
            data = await reader.readline()
            received.append(data)
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(handler, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]

        async with server:
            raw = {
                "session_id": "sess-codex-001",
                "cwd": "/projects/codex-app",
                "message": "Codex wants to run a command",
                "tool_name": "Bash",
            }
            process_hook_event(raw, "PermissionRequest", provider="codex",
                               host="127.0.0.1", port=port)
            await asyncio.sleep(0.2)

        assert len(received) == 1
        parsed = json.loads(received[0].decode().strip())
        assert parsed["hook_event_name"] == "PermissionRequest"
        assert parsed["category"] == "permission"
        assert parsed["provider"] == "codex"
        assert parsed["session"]["provider"] == "codex"
        assert parsed["session"]["project_name"] == "codex-app"

    @pytest.mark.asyncio
    async def test_process_codex_stop_event(self):
        """Codex Stop -> DONE, forwarded with provider=codex."""
        received = []

        async def handler(reader, writer):
            data = await reader.readline()
            received.append(data)
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(handler, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]

        async with server:
            raw = {
                "session_id": "sess-codex-002",
                "cwd": "/projects/codex-app",
                "final_response": "Task completed successfully",
            }
            process_hook_event(raw, "Stop", provider="codex",
                               host="127.0.0.1", port=port)
            await asyncio.sleep(0.2)

        assert len(received) == 1
        parsed = json.loads(received[0].decode().strip())
        assert parsed["category"] == "done"
        assert parsed["provider"] == "codex"
        assert parsed["session"]["provider"] == "codex"

    @pytest.mark.asyncio
    async def test_process_codex_session_start(self):
        """Codex SessionStart -> IDLE, forwarded with provider=codex."""
        received = []

        async def handler(reader, writer):
            data = await reader.readline()
            received.append(data)
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(handler, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]

        async with server:
            raw = {
                "session_id": "sess-codex-003",
                "cwd": "/projects/codex-app",
            }
            process_hook_event(raw, "SessionStart", provider="codex",
                               host="127.0.0.1", port=port)
            await asyncio.sleep(0.2)

        assert len(received) == 1
        parsed = json.loads(received[0].decode().strip())
        assert parsed["category"] == "idle"
        assert parsed["provider"] == "codex"
        assert parsed["hook_event_name"] == "SessionStart"

    @pytest.mark.asyncio
    async def test_process_legacy_claude_code_still_works(self):
        """process_hook_event without provider defaults to claude_code."""
        received = []

        async def handler(reader, writer):
            data = await reader.readline()
            received.append(data)
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(handler, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]

        async with server:
            raw = {
                "session_id": "sess-004",
                "cwd": "/projects/my-app",
                "notification_type": "idle_prompt",
            }
            process_hook_event(raw, "Notification", host="127.0.0.1", port=port)
            await asyncio.sleep(0.2)

        assert len(received) == 1
        parsed = json.loads(received[0].decode().strip())
        assert parsed["provider"] == "claude_code"
        assert parsed["session"]["provider"] == "claude_code"

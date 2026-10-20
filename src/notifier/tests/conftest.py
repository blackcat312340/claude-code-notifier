import pytest
import tempfile
import json
from pathlib import Path


@pytest.fixture(autouse=True)
def _no_real_feishu_webhook(monkeypatch):
    """Guarantee tests never POST to a real Feishu group robot.

    A developer machine may carry a live webhook in
    ~/.config/claude-code-notifier/feishu.json. Any test path that calls
    send_feishu_notification(event) without an explicit ``environ`` (e.g. the
    hook-level process_hook_event tests) would otherwise hit the real endpoint
    and spam the group. Neutralize the config loader so the webhook URL is
    empty; tests that pass an explicit environ still exercise the code against
    a mock/fake endpoint only.
    """
    monkeypatch.setattr(
        "notifier.core.feishu.load_feishu_config",
        lambda path=None: {},
    )


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for test file operations."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def sample_hook_payload():
    """Return a standard Claude Code hook JSON payload for tests."""
    return {
        "session_id": "test-session-001",
        "cwd": "D:/code/my-project",
        "transcript_path": "D:/code/my-project/.claude/transcripts/test.md",
        "notification_type": "permission_prompt",
        "message": "Claude wants to run: npm install",
    }

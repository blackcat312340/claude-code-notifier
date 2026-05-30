import pytest
import tempfile
import json
from pathlib import Path


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

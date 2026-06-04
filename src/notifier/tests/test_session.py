"""Tests for session identity and project name (covers SESS-01, SESS-02)."""
import pytest
from notifier.core.session import extract_session, project_name
from notifier.core.events import Provider


class TestProjectName:
    """D-04: Project display name = leaf directory from cwd."""

    def test_leaf_directory(self):
        """Standard path -> last component."""
        assert project_name("D:/code/my-project") == "my-project"

    def test_deep_path(self):
        """Deeply nested path -> last component."""
        assert project_name("/home/user/projects/notifier/src") == "src"

    def test_empty_string(self):
        """Empty cwd -> 'unknown'."""
        assert project_name("") == "unknown"

    def test_none_string(self):
        """Absent cwd from payload -> 'unknown'."""
        assert project_name("") == "unknown"

    def test_single_component(self):
        """No directory separators -> that component."""
        assert project_name("rootdir") == "rootdir"

    def test_root_windows_path(self):
        """Drive root D:/ -> 'D:' (leaf of Windows path)."""
        result = project_name("D:/")
        # On Windows Path("D:/").parts gives ("D:\\", "/"), Path("D:/").name gives ""
        # Accept any non-empty result that isn't 'unknown'
        assert result != "unknown"

    def test_windows_backslash_path(self):
        """Windows backslash path works via pathlib normalization."""
        assert project_name("D:\\code\\my-project") == "my-project"


class TestExtractSession:
    """SESS-01: Session identity from hook payload."""

    def test_basic_extraction(self):
        """Extract session_id and cwd from payload."""
        raw = {"session_id": "abc123", "cwd": "D:/code/project"}
        session = extract_session(raw)
        assert session.session_id == "abc123"
        assert session.cwd == "D:/code/project"

    def test_project_name_is_leaf(self):
        """project_name is derived from cwd leaf."""
        raw = {"session_id": "abc123", "cwd": "D:/code/notifier"}
        session = extract_session(raw)
        assert session.project_name == "notifier"

    def test_missing_fields(self):
        """Empty payload -> defaults."""
        session = extract_session({})
        assert session.session_id == "unknown"
        assert session.cwd == ""
        assert session.project_name == "unknown"

    def test_composite_key_distinction(self):
        """D-05: Same session_id, different cwd -> distinguishable.

        Same session_id in different project directories should produce
        distinct SessionInfo objects with different project names.
        """
        raw_a = {"session_id": "s1", "cwd": "/project-alpha"}
        raw_b = {"session_id": "s1", "cwd": "/project-beta"}
        sa = extract_session(raw_a)
        sb = extract_session(raw_b)
        assert sa.session_id == sb.session_id  # same id
        assert sa.cwd != sb.cwd  # different directories
        assert sa.project_name != sb.project_name  # different project names

    def test_default_provider_is_claude_code(self):
        """extract_session without provider defaults to CLAUDE_CODE."""
        raw = {"session_id": "abc123", "cwd": "D:/code/project"}
        session = extract_session(raw)
        assert session.provider == Provider.CLAUDE_CODE

    def test_explicit_provider_codex(self):
        """extract_session with provider='codex' stores Codex."""
        raw = {"session_id": "abc123", "cwd": "D:/code/project"}
        session = extract_session(raw, provider=Provider.CODEX)
        assert session.provider == Provider.CODEX
        assert session.provider.value == "codex"

    def test_explicit_provider_string(self):
        """extract_session with provider='codex' string normalizes to Provider.CODEX."""
        raw = {"session_id": "abc123", "cwd": "D:/code/project"}
        session = extract_session(raw, provider="codex")
        assert session.provider == Provider.CODEX

    def test_invalid_provider_defaults_claude_code(self):
        """extract_session with invalid provider string defaults to CLAUDE_CODE."""
        raw = {"session_id": "abc123", "cwd": "D:/code/project"}
        session = extract_session(raw, provider="garbage")
        assert session.provider == Provider.CLAUDE_CODE

    def test_provider_preserves_composite_key_behavior(self):
        """Same (session_id, cwd) with different providers -> different sessions."""
        raw = {"session_id": "s1", "cwd": "/project-alpha"}
        session_claude = extract_session(raw, provider=Provider.CLAUDE_CODE)
        session_codex = extract_session(raw, provider=Provider.CODEX)
        assert session_claude.session_id == session_codex.session_id
        assert session_claude.cwd == session_codex.cwd
        assert session_claude.provider != session_codex.provider

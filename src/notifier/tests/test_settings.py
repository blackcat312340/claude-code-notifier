"""Tests for hook config installation (covers HOOK-01)."""
import pytest
import json
from pathlib import Path
from notifier.core.settings import (
    install_hooks,
    HOOK_ENTRIES,
    NOTIFIER_OWNERSHIP_FILE,
)


class TestHookEntriesStructure:
    """D-02/D-08: Verify 4 hook config entries across 3 event types."""

    def test_has_session_start(self):
        assert "SessionStart" in HOOK_ENTRIES

    def test_has_notification(self):
        assert "Notification" in HOOK_ENTRIES

    def test_has_stop(self):
        assert "Stop" in HOOK_ENTRIES

    def test_notification_has_two_matchers(self):
        """Notification has explicit matchers per_prompt and idle_prompt."""
        entries = HOOK_ENTRIES["Notification"]
        assert len(entries) == 2
        matchers = [e.get("matcher") for e in entries]
        assert "permission_prompt" in matchers
        assert "idle_prompt" in matchers

    def test_session_start_has_no_matcher(self):
        """SessionStart is unconditional -- no matcher field."""
        entries = HOOK_ENTRIES["SessionStart"]
        assert len(entries) == 1
        assert "matcher" not in entries[0]

    def test_stop_has_no_matcher(self):
        """Stop is unconditional -- no matcher field."""
        entries = HOOK_ENTRIES["Stop"]
        assert len(entries) == 1
        assert "matcher" not in entries[0]

    def test_all_entries_have_timeout(self):
        """Every hook entry specifies a timeout."""
        for event_type, entries in HOOK_ENTRIES.items():
            for entry in entries:
                hooks = entry.get("hooks", [])
                for hook in hooks:
                    assert "timeout" in hook, f"{event_type} entry missing timeout"

    def test_all_entries_use_command_type(self):
        """Every hook entry uses type: command."""
        for event_type, entries in HOOK_ENTRIES.items():
            for entry in entries:
                hooks = entry.get("hooks", [])
                for hook in hooks:
                    assert hook.get("type") == "command", (
                        f"{event_type} entry has wrong type"
                    )


class TestInstallHooks:
    """HOOK-01: Install hooks without destroying unrelated settings."""

    def test_preserves_existing_settings(self, temp_dir):
        """D-07: Unrelated keys survive the merge."""
        settings_path = temp_dir / "settings.json"
        original = {
            "theme": "dark",
            "custom_commands": {"fix": "git commit --amend"},
            "project_overrides": {
                "my-project": {"custom_commands": {"test": "pytest -x"}}
            },
        }
        settings_path.write_text(json.dumps(original))

        ownership_path = temp_dir / "ownership.json"
        install_hooks(settings_path=settings_path, ownership_path=ownership_path)

        result = json.loads(settings_path.read_text())
        assert result["theme"] == "dark"
        assert result["custom_commands"]["fix"] == "git commit --amend"
        assert result["project_overrides"]["my-project"]["custom_commands"]["test"] == "pytest -x"

    def test_adds_hooks_key(self, temp_dir):
        """The hooks key is added to settings.json."""
        settings_path = temp_dir / "settings.json"
        settings_path.write_text(json.dumps({"theme": "dark"}))

        ownership_path = temp_dir / "ownership.json"
        install_hooks(settings_path=settings_path, ownership_path=ownership_path)

        result = json.loads(settings_path.read_text())
        assert "hooks" in result

    def test_adds_all_event_types(self, temp_dir):
        """All 4 hook entries are present after install."""
        settings_path = temp_dir / "settings.json"
        settings_path.write_text(json.dumps({}))

        ownership_path = temp_dir / "ownership.json"
        install_hooks(settings_path=settings_path, ownership_path=ownership_path)

        result = json.loads(settings_path.read_text())
        hooks = result["hooks"]
        assert "SessionStart" in hooks
        assert "Notification" in hooks
        assert "Stop" in hooks

    def test_creates_ownership_file(self, temp_dir):
        """D-09: Ownership file is created with correct marker."""
        settings_path = temp_dir / "settings.json"
        settings_path.write_text(json.dumps({}))

        ownership_path = temp_dir / "ownership.json"
        install_hooks(settings_path=settings_path, ownership_path=ownership_path)

        assert ownership_path.exists()
        ownership = json.loads(ownership_path.read_text())
        assert ownership["tool"] == "claude-code-notifier"
        assert ownership["version"] == "0.1.0"
        assert "installed_at" in ownership
        assert "SessionStart" in ownership["hook_event_types"]

    def test_non_existent_settings_creates_new(self, temp_dir):
        """If settings.json doesn't exist, it is created."""
        settings_path = temp_dir / "nonexistent" / "settings.json"
        ownership_path = temp_dir / "ownership.json"

        install_hooks(settings_path=settings_path, ownership_path=ownership_path)

        assert settings_path.exists()
        result = json.loads(settings_path.read_text())
        assert "hooks" in result

    def test_preserves_existing_hooks_from_other_tools(self, temp_dir):
        """Existing hooks from other tools are preserved (ADDITIVE merge)."""
        settings_path = temp_dir / "settings.json"
        original = {
            "hooks": {
                "PrePush": [
                    {"hooks": [{"type": "command", "command": "lint-check"}]}
                ]
            }
        }
        settings_path.write_text(json.dumps(original))

        ownership_path = temp_dir / "ownership.json"
        install_hooks(settings_path=settings_path, ownership_path=ownership_path)

        result = json.loads(settings_path.read_text())
        assert "PrePush" in result["hooks"], "Other tool's hooks were deleted"
        assert "SessionStart" in result["hooks"], "Notifier hooks were not added"

    def test_idempotent_install(self, temp_dir):
        """Running install twice produces the same result (no duplicate entries)."""
        settings_path = temp_dir / "settings.json"
        settings_path.write_text(json.dumps({"theme": "light"}))

        ownership_path = temp_dir / "ownership.json"
        install_hooks(settings_path=settings_path, ownership_path=ownership_path)
        install_hooks(settings_path=settings_path, ownership_path=ownership_path)

        result = json.loads(settings_path.read_text())
        assert result["theme"] == "light"
        assert len(result["hooks"]["SessionStart"]) == 1
        assert len(result["hooks"]["Notification"]) == 2
        assert len(result["hooks"]["Stop"]) == 1

    def test_handles_corrupt_settings_gracefully(self, temp_dir):
        """If settings.json has invalid JSON, it's replaced with new config."""
        settings_path = temp_dir / "settings.json"
        settings_path.write_text("this is not json")

        ownership_path = temp_dir / "ownership.json"
        result = install_hooks(settings_path=settings_path, ownership_path=ownership_path)

        assert result is True
        parsed = json.loads(settings_path.read_text())
        assert "hooks" in parsed

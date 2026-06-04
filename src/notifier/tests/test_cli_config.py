"""Tests for unified notifier-config install CLI (covers D-17)."""
import json
from typer.testing import CliRunner
from notifier.cli.config import app


runner = CliRunner()


class TestUnifiedInstallCLI:
    """D-17: notifier-config install installs both providers."""

    def test_installs_claude_code_hooks(self, temp_dir):
        """CLI install creates Claude Code settings.json."""
        settings_path = temp_dir / "claude" / "settings.json"
        ownership_path = temp_dir / "ownership.json"
        codex_hooks = temp_dir / "codex" / "hooks.json"
        codex_own = temp_dir / "codex-own.json"

        result = runner.invoke(app, [
            "--settings", str(settings_path),
            "--ownership", str(ownership_path),
            "--codex-hooks", str(codex_hooks),
            "--codex-ownership", str(codex_own),
        ])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert settings_path.exists()
        parsed = json.loads(settings_path.read_text())
        assert "hooks" in parsed
        assert "SessionStart" in parsed["hooks"]

    def test_installs_codex_hooks(self, temp_dir):
        """CLI install creates Codex hooks.json."""
        settings_path = temp_dir / "claude" / "settings.json"
        ownership_path = temp_dir / "ownership.json"
        codex_hooks = temp_dir / "codex" / "hooks.json"
        codex_own = temp_dir / "codex-own.json"

        result = runner.invoke(app, [
            "--settings", str(settings_path),
            "--ownership", str(ownership_path),
            "--codex-hooks", str(codex_hooks),
            "--codex-ownership", str(codex_own),
        ])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert codex_hooks.exists()
        parsed = json.loads(codex_hooks.read_text())
        assert "SessionStart" in parsed
        assert "PermissionRequest" in parsed
        assert "Stop" in parsed

    def test_output_contains_claude_chinese_status(self, temp_dir):
        """CLI output reports Claude Code status in Chinese."""
        settings_path = temp_dir / "claude" / "settings.json"
        ownership_path = temp_dir / "ownership.json"
        codex_hooks = temp_dir / "codex" / "hooks.json"
        codex_own = temp_dir / "codex-own.json"

        result = runner.invoke(app, [
            "--settings", str(settings_path),
            "--ownership", str(ownership_path),
            "--codex-hooks", str(codex_hooks),
            "--codex-ownership", str(codex_own),
        ])

        assert "Claude Code hooks: 已安装" in result.output

    def test_output_contains_codex_chinese_status(self, temp_dir):
        """CLI output reports Codex status in Chinese."""
        settings_path = temp_dir / "claude" / "settings.json"
        ownership_path = temp_dir / "ownership.json"
        codex_hooks = temp_dir / "codex" / "hooks.json"
        codex_own = temp_dir / "codex-own.json"

        result = runner.invoke(app, [
            "--settings", str(settings_path),
            "--ownership", str(ownership_path),
            "--codex-hooks", str(codex_hooks),
            "--codex-ownership", str(codex_own),
        ])

        assert "Codex hooks: 已安装" in result.output

    def test_preserves_existing_claude_settings(self, temp_dir):
        """Existing Claude settings survive CLI install."""
        settings_path = temp_dir / "claude" / "settings.json"
        original = {"theme": "dark", "custom_commands": {"fix": "git commit --amend"}}
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(original))

        ownership_path = temp_dir / "ownership.json"
        codex_hooks = temp_dir / "codex" / "hooks.json"
        codex_own = temp_dir / "codex-own.json"

        result = runner.invoke(app, [
            "--settings", str(settings_path),
            "--ownership", str(ownership_path),
            "--codex-hooks", str(codex_hooks),
            "--codex-ownership", str(codex_own),
        ])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        parsed = json.loads(settings_path.read_text())
        assert parsed["theme"] == "dark"
        assert parsed["custom_commands"]["fix"] == "git commit --amend"
        assert "hooks" in parsed

    def test_creates_ownership_files_for_both_providers(self, temp_dir):
        """Both Claude Code and Codex ownership files are created."""
        settings_path = temp_dir / "claude" / "settings.json"
        ownership_path = temp_dir / "ownership.json"
        codex_hooks = temp_dir / "codex" / "hooks.json"
        codex_own = temp_dir / "codex-own.json"

        result = runner.invoke(app, [
            "--settings", str(settings_path),
            "--ownership", str(ownership_path),
            "--codex-hooks", str(codex_hooks),
            "--codex-ownership", str(codex_own),
        ])

        assert result.exit_code == 0
        assert ownership_path.exists()
        assert codex_own.exists()
        claude_own = json.loads(ownership_path.read_text())
        codex_own_data = json.loads(codex_own.read_text())
        assert claude_own["tool"] == "claude-code-notifier"
        assert codex_own_data["tool"] == "claude-code-notifier"

    def test_existing_claude_settings_path_options_still_work(self, temp_dir):
        """The --settings and --ownership options still work for Claude."""
        settings_path = temp_dir / "custom-settings.json"
        ownership_path = temp_dir / "custom-ownership.json"
        codex_hooks = temp_dir / "codex" / "hooks.json"
        codex_own = temp_dir / "codex-own.json"

        result = runner.invoke(app, [
            "--settings", str(settings_path),
            "--ownership", str(ownership_path),
            "--codex-hooks", str(codex_hooks),
            "--codex-ownership", str(codex_own),
        ])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert settings_path.exists()
        assert ownership_path.exists()
        result_output = result.output.replace("\n", " ")
        assert "Claude Code hooks: 已安装" in result_output
        assert "Codex hooks: 已安装" in result_output

    def test_install_idempotent_via_cli(self, temp_dir):
        """Running install twice via CLI produces the same result (no duplicates)."""
        settings_path = temp_dir / "claude" / "settings.json"
        ownership_path = temp_dir / "ownership.json"
        codex_hooks = temp_dir / "codex" / "hooks.json"
        codex_own = temp_dir / "codex-own.json"

        args = [
            "--settings", str(settings_path),
            "--ownership", str(ownership_path),
            "--codex-hooks", str(codex_hooks),
            "--codex-ownership", str(codex_own),
        ]

        result1 = runner.invoke(app, args)
        assert result1.exit_code == 0

        result2 = runner.invoke(app, args)
        assert result2.exit_code == 0

        # Claude Code: no duplicate entries
        claude = json.loads(settings_path.read_text())
        assert len(claude["hooks"]["SessionStart"]) == 1
        assert len(claude["hooks"]["Stop"]) == 1

        # Codex: no duplicate entries
        codex = json.loads(codex_hooks.read_text())
        assert len(codex["SessionStart"]) == 1
        assert len(codex["Stop"]) == 1

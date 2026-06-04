import typer
from notifier.core.settings import (
    install_hooks,
    install_codex_hooks,
    SETTINGS_FILE,
    NOTIFIER_OWNERSHIP_FILE,
    CODEX_HOOKS_FILE,
    CODEX_OWNERSHIP_FILE,
)

app = typer.Typer(
    name="notifier-config",
    help="Manage notifier Claude Code and Codex hook configuration",
    add_completion=False,
)


@app.command()
def install(
    settings_path: str = typer.Option(
        None,
        "--settings",
        "-s",
        help="Path to Claude Code settings.json (default: ~/.claude/settings.json)",
    ),
    ownership_path: str = typer.Option(
        None,
        "--ownership",
        "-o",
        help="Path to notifier ownership file (default: ~/.claude/.notifier-ownership.json)",
    ),
    codex_hooks_path: str = typer.Option(
        None,
        "--codex-hooks",
        help="Path to Codex hooks.json (default: ~/.codex/hooks.json)",
    ),
    codex_ownership_path: str = typer.Option(
        None,
        "--codex-ownership",
        help="Path to Codex ownership file (default: ~/.codex/.notifier-ownership.json)",
    ),
):
    """Install notifier hook entries into Claude Code and Codex configurations.

    Per D-07: Only the 'hooks' key is modified in Claude Code settings. All other
    user settings (themes, custom commands, project overrides) are preserved.

    Per D-09: Ownership is tracked in separate config files, NOT by adding metadata
    keys to the hook entries.

    Per D-16: Codex install is non-destructive; only notifier-owned entries are
    managed and unrelated Codex hooks/settings are preserved.

    Per D-17: This command installs hooks for both providers and reports each
    provider's install status.
    """
    from pathlib import Path

    s_path = Path(settings_path) if settings_path else SETTINGS_FILE
    o_path = Path(ownership_path) if ownership_path else NOTIFIER_OWNERSHIP_FILE
    cx_hooks = Path(codex_hooks_path) if codex_hooks_path else CODEX_HOOKS_FILE
    cx_own = Path(codex_ownership_path) if codex_ownership_path else CODEX_OWNERSHIP_FILE

    # Install Claude Code hooks
    install_hooks(settings_path=s_path, ownership_path=o_path)
    typer.echo(f"Claude Code hooks: 已安装 ({s_path})")
    typer.echo(f"Claude Code ownership: {o_path}")

    # Install Codex hooks
    install_codex_hooks(hooks_path=cx_hooks, ownership_path=cx_own)
    typer.echo(f"Codex hooks: 已安装 ({cx_hooks})")
    typer.echo(f"Codex ownership: {cx_own}")

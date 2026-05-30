import typer
from notifier.core.settings import install_hooks, SETTINGS_FILE, NOTIFIER_OWNERSHIP_FILE

app = typer.Typer(
    name="notifier-config",
    help="Manage notifier Claude Code hook configuration",
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
):
    """Install notifier hook entries into Claude Code settings.json.

    Per D-07: Only the 'hooks' key is modified. All other user settings
    (themes, custom commands, project overrides) are preserved.

    Per D-09: Ownership is tracked in a separate config file, NOT by
    adding metadata keys to the Claude Code hook entries.
    """
    from pathlib import Path

    s_path = Path(settings_path) if settings_path else SETTINGS_FILE
    o_path = Path(ownership_path) if ownership_path else NOTIFIER_OWNERSHIP_FILE

    install_hooks(settings_path=s_path, ownership_path=o_path)
    typer.echo(f"Hooks installed in {s_path}")
    typer.echo(f"Ownership tracked in {o_path}")

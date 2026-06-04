import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from mergedeep import merge, Strategy

# Claude Code settings file path
SETTINGS_FILE = Path.home() / ".claude" / "settings.json"

# Notifier ownership tracking file (per D-09: separate from Claude settings)
NOTIFIER_OWNERSHIP_FILE = Path.home() / ".claude" / ".notifier-ownership.json"

# Codex settings file paths (per D-15: user-level install)
CODEX_HOOKS_FILE = Path.home() / ".codex" / "hooks.json"
CODEX_OWNERSHIP_FILE = Path.home() / ".codex" / ".notifier-ownership.json"

def _build_hook_entries():
    """Build hook entries using the current Python executable absolute path.

    Using sys.executable ensures Claude Code can invoke the hook regardless
    of which project directory or virtual environment it runs in.
    The path is quoted to handle spaces (e.g., Program Files).
    """
    import sys
    python = sys.executable
    return {
        "SessionStart": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": f'"{python}" -m notifier.cli.hook SessionStart',
                        "timeout": 10,
                    }
                ]
            }
        ],
        "Notification": [
            {
                "matcher": "permission_prompt",
                "hooks": [
                    {
                        "type": "command",
                        "command": f'"{python}" -m notifier.cli.hook Notification',
                        "timeout": 10,
                    }
                ],
            },
            {
                "matcher": "idle_prompt",
                "hooks": [
                    {
                        "type": "command",
                        "command": f'"{python}" -m notifier.cli.hook Notification',
                        "timeout": 10,
                    }
                ],
            },
        ],
        "Stop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": f'"{python}" -m notifier.cli.hook Stop',
                        "timeout": 10,
                    }
                ]
            }
        ],
    }


# The 4 hook entries to install (per D-02/D-08, reconciled with research findings)
# Built at import time with the current Python executable absolute path.
HOOK_ENTRIES: Dict[str, Any] = _build_hook_entries()

OWNERSHIP_MARKER = {
    "tool": "claude-code-notifier",
    "version": "0.1.0",
    "installed_at": None,  # filled at install time
    "hook_event_types": ["SessionStart", "Notification", "Stop"],
    "matchers": {"Notification": ["permission_prompt", "idle_prompt"]},
}


def _build_codex_hook_entries():
    """Build Codex hook entries using the current Python executable absolute path.

    Codex hooks use top-level event names as keys and invoke the
    provider-aware CLI so the hook command passes provider=codex.
    Event coverage reflects official Codex lifecycle hooks:
    SessionStart, PermissionRequest, and Stop.
    """
    import sys
    python = sys.executable
    return {
        "SessionStart": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": f'"{python}" -m notifier.cli.hook SessionStart codex',
                        "timeout": 10,
                    }
                ]
            }
        ],
        "PermissionRequest": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": f'"{python}" -m notifier.cli.hook PermissionRequest codex',
                        "timeout": 10,
                    }
                ]
            }
        ],
        "Stop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": f'"{python}" -m notifier.cli.hook Stop codex',
                        "timeout": 10,
                    }
                ]
            }
        ],
    }


# Codex hook entries built at import time with the current Python executable.
CODEX_HOOK_ENTRIES: Dict[str, Any] = _build_codex_hook_entries()

CODEX_OWNERSHIP_MARKER = {
    "tool": "claude-code-notifier",
    "version": "0.1.0",
    "installed_at": None,  # filled at install time
    "hook_event_types": ["SessionStart", "PermissionRequest", "Stop"],
}


def _read_json(path: Path) -> Dict[str, Any]:
    """Read JSON file, returning empty dict if file doesn't exist or is invalid."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logging.warning("Could not read %s: %s. Starting fresh.", path, exc)
        return {}


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    """Write JSON data to file atomically (write to temp, rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(path)


def _is_notifier_entry(entry: Dict[str, Any]) -> bool:
    """Check if a hook entry is owned by the notifier (contains notifier hook module reference)."""
    hooks = entry.get("hooks", [])
    for hook in hooks:
        cmd = hook.get("command", "")
        if "notifier.cli.hook" in cmd or "notifier-hook" in cmd:
            return True
    return False


def install_hooks(
    settings_path: Optional[Path] = None,
    ownership_path: Optional[Path] = None,
) -> bool:
    """Deep-merge notifier hook entries into Claude Code settings.json.

    Per D-07: Merges only the 'hooks' key. All other user settings
    (themes, custom commands, project overrides, other hook tools)
    are preserved untouched.

    Per D-09: Tracks ownership in a separate notifier config file,
    NOT by adding metadata keys to Claude Code hook entries.

    Args:
        settings_path: Path to settings.json (default: ~/.claude/settings.json).
        ownership_path: Path to ownership file (default: ~/.claude/.notifier-ownership.json).

    Returns:
        True if hooks were installed successfully.
    """
    s_path = settings_path or SETTINGS_FILE
    o_path = ownership_path or NOTIFIER_OWNERSHIP_FILE

    # Step 1: Read existing settings
    existing = _read_json(s_path)

    # Step 2: Strip existing notifier hook entries to ensure idempotency.
    # mergedeep's ADDITIVE strategy appends lists, so a second install would
    # duplicate entries. We first remove any hooks referencing "notifier-hook",
    # then merge fresh entries.
    if "hooks" in existing:
        for event_type in list(existing["hooks"].keys()):
            entries = existing["hooks"][event_type]
            if isinstance(entries, list):
                existing["hooks"][event_type] = [
                    e
                    for e in entries
                    if not _is_notifier_entry(e)
                ]
            # Clean up empty event type keys
            if not existing["hooks"][event_type]:
                del existing["hooks"][event_type]

    # Step 3: Deep-merge only the hooks key (per D-07, mergedeep ADDITIVE)
    # ADDITIVE strategy: merges lists by appending, merges dicts recursively
    merge(existing, {"hooks": HOOK_ENTRIES}, strategy=Strategy.ADDITIVE)

    # Step 3: Write back the full settings file
    _write_json(s_path, existing)

    # Step 4: Write ownership tracking file (per D-09)
    import datetime
    ownership = dict(OWNERSHIP_MARKER)
    ownership["installed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    _write_json(o_path, ownership)

    logging.info(
        "Notifier hooks installed into %s (ownership tracked in %s)",
        s_path,
        o_path,
    )
    return True

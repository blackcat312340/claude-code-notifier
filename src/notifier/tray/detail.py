"""Windows native detail popup via MessageBox (D-05, D-06)."""
import ctypes


def show_detail(event):
    """Show event details in a Windows MessageBox.

    Per D-05: Shows timestamp, project name, event category, hook event type,
    message content.
    Per D-06: Project path displayed — user can copy or navigate manually.

    Uses ctypes to call MessageBoxW — zero dependencies, always available on Windows.
    """
    cat = event.category.value if hasattr(event.category, 'value') else str(event.category)
    project = event.session.project_name
    ts = event.timestamp[:19] if event.timestamp else "unknown"
    hook_type = event.hook_event_name
    path = event.session.cwd or "(unknown)"
    msg = event.message or "(no message)"
    if len(msg) > 300:
        msg = msg[:300] + "..."

    body = (
        f"Category:  {cat}\n"
        f"Time:      {ts}\n"
        f"Event:     {hook_type}\n"
        f"Path:      {path}\n"
        f"{'─' * 40}\n"
        f"{msg}"
    )

    ctypes.windll.user32.MessageBoxW(
        0, body, f"Claude Code Notifier - {project}", 0x40
    )

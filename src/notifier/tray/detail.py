"""Windows native detail popup via MessageBox (D-05, D-06)."""
import ctypes
from notifier.core.text import provider_label, category_label


def _build_detail_body(event):
    """Build the detail body text for a single event.

    Per D-02: provider source is visible.
    Per D-11, D-12, D-13: Chinese-first labels, technical values remain recognizable.
    Per T-031-06: long messages are truncated.
    """
    provider = provider_label(event.provider)
    cat_val = (
        event.category.value
        if hasattr(event.category, "value")
        else str(event.category)
    )
    cat_cn = category_label(event.category)
    project = event.session.project_name
    ts = event.timestamp[:19] if event.timestamp else "unknown"
    hook_type = event.hook_event_name
    path = event.session.cwd or "(unknown)"
    msg = event.message or "(no message)"
    if len(msg) > 300:
        msg = msg[:300] + "..."

    body = (
        f"来源:      {provider}\n"
        f"类别:      {cat_val} ({cat_cn})\n"
        f"时间:      {ts}\n"
        f"事件:      {hook_type}\n"
        f"项目路径:  {path}\n"
        f"{'─' * 40}\n"
        f"{msg}"
    )

    return body


def show_detail(event):
    """Show event details in a Windows MessageBox.

    Per D-05: Shows timestamp, project name, event category, hook event type,
    message content, and provider source.
    Per D-06: Project path displayed — user can copy or navigate manually.
    Per D-11: Chinese-first body labels. Window title keeps app name stable.

    Uses ctypes to call MessageBoxW — zero dependencies, always available on Windows.
    """
    body = _build_detail_body(event)
    ctypes.windll.user32.MessageBoxW(
        0, body, f"Claude Code Notifier - {event.session.project_name}", 0x40
    )

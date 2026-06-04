"""Centralized Chinese-first display labels and notification text helpers.

Per D-11, D-13, D-14: User-visible copy is Chinese-first, provider names and
technical identifiers remain recognizable, and copy is concise tool-style.
"""

from typing import Union
from datetime import datetime, timezone

from notifier.core.events import Provider, EventCategory, NotifierEvent


def provider_label(provider: Union[Provider, str]) -> str:
    """Return human-readable provider display name.

    Claude Code -> "Claude Code"
    Codex      -> "Codex"
    Per D-13: provider names remain recognizable.
    Unknown values degrade to a readable string without raising.
    """
    if isinstance(provider, Provider):
        if provider == Provider.CLAUDE_CODE:
            return "Claude Code"
        if provider == Provider.CODEX:
            return "Codex"
        return str(provider.value).replace("_", " ").title()

    # String fallback
    s = str(provider).lower()
    if s in ("claude_code", "claude code"):
        return "Claude Code"
    if s == "codex":
        return "Codex"
    return str(provider).replace("_", " ").title()


def category_label(category: Union[EventCategory, str]) -> str:
    """Return concise Chinese category label.

    Per D-14: tool-style Chinese.
    permission -> 需要授权
    idle       -> 等待输入
    done       -> 任务已完成
    error      -> 需要检查
    Unknown values degrade to the raw value string.
    """
    val = category.value if isinstance(category, EventCategory) else str(category)
    mapping = {
        "permission": "需要授权",
        "idle": "等待输入",
        "done": "任务已完成",
        "error": "需要检查",
    }
    return mapping.get(val, val)


def notification_title(event: NotifierEvent) -> str:
    """Build notification title: provider source + project name.

    Per D-02: shows event source without renaming app_id.
    Examples: "Codex - notifier", "Claude Code - my-project"
    """
    provider = provider_label(event.provider)
    project = event.session.project_name
    return f"{provider} - {project}"


def notification_body(event: NotifierEvent) -> str:
    """Build concise Chinese-first notification body.

    Per D-12, D-14: covers notification copy, concise tool-style.
    Includes category label and, when available, message detail.
    Per T-031-06: messages are truncated to 200 chars to prevent
    overly long notification text.
    Examples: "需要授权 - Bash", "任务已完成", "等待输入"
    """
    label = category_label(event.category)
    detail = event.message
    if detail:
        # Truncate long messages (T-031-06: DoS via long messages)
        if len(detail) > 200:
            detail = detail[:200] + "..."
        return f"{label} - {detail}"
    return label


def event_menu_label(event: NotifierEvent, relative_time: str = "") -> str:
    """Build tray menu item label with provider, stable category, and Chinese label.

    Per D-02, D-13: provider source visible, category values remain recognizable.
    Format: "{provider} - {category_value} - {category_label} (relative_time)"
    Example: "Codex - permission - 需要授权 (刚刚)"
    """
    provider = provider_label(event.provider)
    cat_val = (
        event.category.value
        if isinstance(event.category, EventCategory)
        else str(event.category)
    )
    cat_label = category_label(event.category)
    label = f"{provider} - {cat_val} - {cat_label}"
    if relative_time:
        label += f" ({relative_time})"
    return label


def relative_time_cn(timestamp: str) -> str:
    """Return concise Chinese relative time from an ISO timestamp.

    Per D-14: concise tool-style.
    < 1 min   -> 刚刚
    = 1 min   -> 1 分钟前
    >= 2 min  -> {N} 分钟前
    Returns empty string on parse error.
    """
    try:
        ts = datetime.fromisoformat(timestamp)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - ts
        mins = int(delta.total_seconds() / 60)
        if mins < 1:
            return "刚刚"
        elif mins == 1:
            return "1 分钟前"
        else:
            return f"{mins} 分钟前"
    except Exception:
        return ""

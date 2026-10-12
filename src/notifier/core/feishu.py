"""Minimal, privacy-first Feishu group-robot delivery for Claude/Codex hooks.

The webhook is a credential. Read it from the environment only, never write
it to repository files or include it in exception logs.
"""
import base64
import hashlib
import hmac
import json
import logging
import os
import socket
import time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from notifier.core.events import EventCategory, NotifierEvent, Provider

_WEBHOOK_HOSTS = {"open.feishu.cn", "open.larksuite.com"}
_WEBHOOK_PREFIX = "/open-apis/bot/v2/hook/"
_TIMEOUT_SECONDS = 3
FEISHU_CONFIG_FILE = Path.home() / ".config" / "claude-code-notifier" / "feishu.json"


def load_feishu_config(path: Path | None = None) -> dict:
    """Read per-user config. Never log the webhook or signing secret."""
    location = FEISHU_CONFIG_FILE if path is None else path
    try:
        if location.stat().st_size > 4096:
            return {}
        data = json.loads(location.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}




def _valid_webhook(url: str) -> bool:
    try:
        p = urlsplit(url)
        return (
            p.scheme == "https"
            and p.hostname in _WEBHOOK_HOSTS
            and p.port in (None, 443)
            and not p.username
            and not p.password
            and not p.fragment
            and not p.query
            and p.path.startswith(_WEBHOOK_PREFIX)
            and bool(p.path[len(_WEBHOOK_PREFIX):])
        )
    except ValueError:
        return False


def _clean(value: object, limit: int = 120) -> str:
    # Never allow untrusted hook input to forge extra notification fields.
    return " ".join(str(value or "").split())[:limit]


def _category(event: NotifierEvent) -> str:
    return event.category.value if isinstance(event.category, EventCategory) else str(event.category)


def _provider(event: NotifierEvent) -> str:
    provider = event.provider.value if isinstance(event.provider, Provider) else str(event.provider)
    return "Codex" if provider == "codex" else "Claude Code"


def _summary(event: NotifierEvent) -> str | None:
    if event.hook_event_name == "SessionStart":
        return None
    if event.hook_event_name == "StopFailure":
        return "执行异常"
    if event.hook_event_name == "TaskCompleted":
        return "任务已标记完成"
    if event.hook_event_name == "Stop":
        return "本轮回复结束"
    if event.hook_event_name == "PermissionRequest" or _category(event) == "permission":
        return "需要授权"
    if _category(event) == "idle":
        return "等待输入"
    if event.hook_event_name == "Notification" and _category(event) == "done":
        return "后台 Agent 已结束"
    return None


def format_feishu_text(event: NotifierEvent, *, device: str = "", include_message: bool = False) -> str | None:
    """Allowlisted text only; do not forward raw_payload or transcripts."""
    summary = _summary(event)
    if not summary:
        return None
    result = [
        f"[Claude Notifier] {_provider(event)} · {summary}",
        f"设备：{_clean(device or socket.gethostname(), 64)}",
        f"项目：{_clean(event.session.project_name, 100)}",
        f"事件：{_clean(event.hook_event_name, 40)}",
    ]
    if event.hook_event_name == "StopFailure":
        result.append(f"原因：{_clean(event.raw_payload.get('error', 'unknown'), 60)}")
    elif event.hook_event_name == "TaskCompleted":
        # Task subject is task metadata (never task_description).
        result.append(f"任务：{_clean(event.raw_payload.get('task_subject', ''), 100)}")
    elif event.hook_event_name == "PermissionRequest":
        result.append(f"工具：{_clean(event.raw_payload.get('tool_name', ''), 60)}")
    elif include_message and event.hook_event_name in ("Stop", "Notification"):
        # Deliberately opt-in. May contain private conversational data.
        result.append(f"消息：{_clean(event.message, 160)}")
    return "\n".join(result)


def build_feishu_payload(text: str, secret: str = "", *, timestamp: int | None = None) -> dict:
    payload = {"msg_type": "text", "content": {"text": text}}
    if secret:
        ts = int(time.time()) if timestamp is None else int(timestamp)
        to_sign = f"{ts}\n{secret}".encode("utf-8")
        signature = base64.b64encode(hmac.new(to_sign, b"", hashlib.sha256).digest()).decode("ascii")
        payload.update({"timestamp": str(ts), "sign": signature})
    return payload


def send_feishu_notification(event: NotifierEvent, *, environ=None) -> bool:
    """Best-effort bounded POST; never changes Claude's permission decisions."""
    if environ is None:
        local = load_feishu_config()
        env = {
            "NOTIFIER_FEISHU_WEBHOOK": local.get("webhook", ""),
            "NOTIFIER_FEISHU_SECRET": local.get("secret", ""),
            "NOTIFIER_DEVICE_NAME": local.get("device", ""),
            "NOTIFIER_FEISHU_INCLUDE_MESSAGE": "1" if local.get("include_message", False) else "0",
        }
        env.update(os.environ)
    else:
        env = environ
    url = str(env.get("NOTIFIER_FEISHU_WEBHOOK") or "").strip()
    if not url:
        return False
    if not _valid_webhook(url):
        logging.warning("Feishu webhook rejected: expected official HTTPS bot URL")
        return False
    text = format_feishu_text(
        event,
        device=env.get("NOTIFIER_DEVICE_NAME", ""),
        include_message=env.get("NOTIFIER_FEISHU_INCLUDE_MESSAGE") == "1",
    )
    if not text:
        return False
    body = json.dumps(
        build_feishu_payload(text, env.get("NOTIFIER_FEISHU_SECRET", "")),
        ensure_ascii=False,
    ).encode("utf-8")
    request = Request(url, data=body, headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
    try:
        with urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                logging.warning("Feishu delivery rejected (HTTP %d)", response.status)
                return False
            result = json.loads(response.read(4096))
            # A successful HTTP status alone does not mean that Feishu accepted the message.
            code = result.get("code", result.get("StatusCode"))
            if code not in (0, "0"):
                logging.warning("Feishu delivery rejected (application code %s)", _clean(code, 30))
                return False
            return True
    except (OSError, ValueError, TypeError) as exc:
        # URL is a bearer credential: do not log the exception itself.
        logging.warning("Feishu delivery failed (%s)", type(exc).__name__)
        return False

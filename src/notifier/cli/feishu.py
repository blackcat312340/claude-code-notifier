"""Interactive, local-only configuration for the Feishu group webhook."""
import argparse
import getpass
import json
import os
import socket
import sys
import tempfile

from notifier.core.events import EventCategory, NotifierEvent, SessionInfo
from notifier.core.feishu import (
    FEISHU_CONFIG_FILE, _valid_webhook, load_feishu_config,
    send_feishu_notification,
)


def save_feishu_config(settings: dict, path=FEISHU_CONFIG_FILE):
    """Write user secrets atomically; POSIX configuration is mode 0600."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".feishu-", suffix=".tmp", dir=str(path.parent))
    try:
        if os.name != "nt":
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(settings, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
        if os.name != "nt":
            os.chmod(path, 0o600)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Configure and test Claude Code Feishu notifications")
    parser.add_argument("action", choices=["setup", "test", "status"])
    args = parser.parse_args(argv)

    if args.action == "setup":
        webhook = getpass.getpass("飞书群机器人的 Webhook URL（隐藏输入）：").strip()
        if not _valid_webhook(webhook):
            print("无效的飞书群机器人 Webhook HTTPS 地址", file=sys.stderr)
            return 2
        secret = getpass.getpass("飞书签名密钥（未启用签名可留空）：").strip()
        device = input(f"设备名称 [{socket.gethostname()}]：").strip() or socket.gethostname()
        save_feishu_config({"webhook": webhook, "secret": secret, "device": device})
        print(f"配置已写入 {FEISHU_CONFIG_FILE}（没有写入 Git 仓库）")
        return 0

    if args.action == "status":
        configured = bool(load_feishu_config().get("webhook") or os.getenv("NOTIFIER_FEISHU_WEBHOOK"))
        print("飞书通知已配置" if configured else "飞书通知未配置")
        return 0 if configured else 1

    sample = NotifierEvent(
        category=EventCategory.DONE,
        session=SessionInfo("feishu-test", os.getcwd(), "notifier-self-test"),
        hook_event_name="Stop",
    )
    if send_feishu_notification(sample):
        print("飞书测试消息已提交，请检查目标群聊")
        return 0
    print("飞书测试发送失败，请检查 Webhook、签名和网络连接", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())

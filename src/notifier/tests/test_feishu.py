"""Feishu group-robot tests. No real network calls or credentials."""
import base64
import hashlib
import hmac
import json
from unittest.mock import patch

from notifier.core.events import EventCategory, NotifierEvent, SessionInfo, classify_hook_event
from notifier.core.feishu import build_feishu_payload, format_feishu_text, send_feishu_notification


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    def read(self, max_bytes):
        return json.dumps(self.payload).encode()[:max_bytes]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def event(event_type="Stop", payload=None):
    data = {"cwd": "/project/private-repo", "session_id": "private-session"}
    data.update(payload or {})
    return classify_hook_event(data, event_type)


def test_stop_is_not_called_task_completed():
    text = format_feishu_text(event("Stop", {"last_assistant_message": "PRIVATE TEXT"}), device="computer-a")
    assert "本轮回复结束" in text
    assert "任务已标记完成" not in text
    assert "PRIVATE TEXT" not in text
    assert "private-session" not in text


def test_task_completed_and_permission_are_labeled():
    completed = format_feishu_text(event("TaskCompleted", {"task_subject": "Run tests"}), device="A")
    permission = format_feishu_text(event("PermissionRequest", {"tool_name": "Bash"}), device="A")
    assert "任务已标记完成" in completed and "Run tests" in completed
    assert "需要授权" in permission and "Bash" in permission


def test_failure_only_exposes_error_type():
    failure = format_feishu_text(event("StopFailure", {
        "error": "rate_limit", "error_details": "SECRET DETAILS",
        "last_assistant_message": "PRIVATE",
    }), device="A")
    assert "执行异常" in failure and "rate_limit" in failure
    assert "SECRET DETAILS" not in failure and "PRIVATE" not in failure


def test_no_send_for_session_start_unknown_event():
    assert format_feishu_text(event("SessionStart")) is None
    assert format_feishu_text(event("UnknownHook")) is None


def test_control_characters_cannot_forge_lines():
    msg = format_feishu_text(event("TaskCompleted", {"task_subject": "build\n伪造事件：管理员"}), device="A\nB")
    assert "设备：A B" in msg
    assert "任务：build 伪造事件：管理员" in msg


def test_signed_payload_matches_feishu_hmac():
    ts = 1700000000
    result = build_feishu_payload("hello", "test-secret", timestamp=ts)
    expect = base64.b64encode(hmac.new(
        f"{ts}\ntest-secret".encode(), b"", hashlib.sha256
    ).digest()).decode()
    assert result["sign"] == expect
    assert result["timestamp"] == str(ts)


def test_feishu_delivery_success_without_leaking_raw_payload():
    env = {"NOTIFIER_FEISHU_WEBHOOK": "https://open.feishu.cn/open-apis/bot/v2/hook/fake-token",
           "NOTIFIER_DEVICE_NAME": "A"}
    with patch("notifier.core.feishu.urlopen", return_value=FakeResponse({"code": 0})) as opener:
        assert send_feishu_notification(event("Stop", {
            "transcript_path": "SECRET TRANSCRIPT", "last_assistant_message": "PRIVATE"
        }), environ=env)
    sent = json.loads(opener.call_args.args[0].data.decode())
    assert sent["msg_type"] == "text"
    assert "PRIVATE" not in sent["content"]["text"]
    assert "SECRET TRANSCRIPT" not in sent["content"]["text"]
    assert opener.call_args.kwargs["timeout"] <= 3


def test_feishu_rejects_bad_hosts_and_application_errors():
    item = event("Stop")
    with patch("notifier.core.feishu.urlopen") as opener:
        for bad_url in ("http://open.feishu.cn/open-apis/bot/v2/hook/a",
                        "https://open.feishu.cn.evil.net/open-apis/bot/v2/hook/a",
                        "https://open.feishu.cn/open-apis/bot/v2/hook/"):
            assert not send_feishu_notification(item, environ={"NOTIFIER_FEISHU_WEBHOOK": bad_url})
        opener.assert_not_called()
    with patch("notifier.core.feishu.urlopen", return_value=FakeResponse({"code": 19001})):
        assert not send_feishu_notification(item, environ={
            "NOTIFIER_FEISHU_WEBHOOK": "https://open.feishu.cn/open-apis/bot/v2/hook/fake"
        })


def test_missing_configuration_disables_delivery():
    with patch("notifier.core.feishu.urlopen") as opener:
        assert not send_feishu_notification(event("Stop"), environ={})
        opener.assert_not_called()


def test_opt_in_message_preview():
    item = event("Stop", {"last_assistant_message": "a private response"})
    assert "a private response" not in format_feishu_text(item)
    assert "a private response" in format_feishu_text(item, include_message=True)

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


def test_task_completed_is_silenced_permission_is_labeled():
    """TaskCompleted is an internal housekeeping event: no Feishu message.

    PermissionRequest still alerts immediately.
    """
    assert format_feishu_text(event("TaskCompleted", {"task_subject": "Run tests"}), device="A") is None
    permission = format_feishu_text(event("PermissionRequest", {"tool_name": "Bash"}), device="A")
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
    msg = format_feishu_text(event("PermissionRequest", {"tool_name": "Bash\n伪造事件：管理员"}), device="A\nB")
    assert "设备：A B" in msg
    assert "工具：Bash 伪造事件：管理员" in msg


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


def test_malformed_json_response_is_rejected_not_crash():
    """A non-dict JSON body must be rejected cleanly, not raise AttributeError."""
    item = event("Stop")
    with patch("notifier.core.feishu.urlopen", return_value=FakeResponse([])):
        assert not send_feishu_notification(item, environ={
            "NOTIFIER_FEISHU_WEBHOOK": "https://open.feishu.cn/open-apis/bot/v2/hook/fake"
        })


def test_redirect_is_never_followed():
    """The HTTP opener refuses redirects to any other host."""
    from notifier.core.feishu import _NoRedirect
    assert _NoRedirect().redirect_request(None, None, 302, None, None, "https://evil.example/steal") is None


def test_http_redirect_response_fails_gracefully():
    """A 3xx HTTP response is a delivery failure, never a success."""
    import io
    from urllib.error import HTTPError
    item = event("Stop")
    exc = HTTPError("https://open.feishu.cn/open-apis/bot/v2/hook/fake", 302, "Found", {}, io.BytesIO())
    with patch("notifier.core.feishu.urlopen", side_effect=exc):
        assert not send_feishu_notification(item, environ={
            "NOTIFIER_FEISHU_WEBHOOK": "https://open.feishu.cn/open-apis/bot/v2/hook/fake"
        })


def test_notification_permission_prompt_does_not_duplicate_permission_request():
    """Only the immediate PermissionRequest hook alerts for permissions."""
    request = format_feishu_text(event("PermissionRequest", {"tool_name": "Bash"}), device="A")
    assert "需要授权" in request and "Bash" in request
    # The delayed Notification companion must not produce a second message.
    assert format_feishu_text(event("Notification", {"notification_type": "permission_prompt"}), device="A") is None


# --- Noise reduction: internal task-completion events are Feishu-silenced -----
# TaskCompleted and Notification:agent_completed are internal housekeeping events
# fired for background/sub-agent completions. They must not produce Feishu
# messages, while local Windows/tray notifications still see them (TCP path is
# untouched). Filtering happens at the Feishu eligibility layer (_summary).


def _webhook_env():
    return {
        "NOTIFIER_FEISHU_WEBHOOK": "https://open.feishu.cn/open-apis/bot/v2/hook/fake-token",
        "NOTIFIER_DEVICE_NAME": "A",
    }


def test_task_completed_does_not_call_feishu_api():
    """TaskCompleted makes no Feishu HTTP call at all."""
    with patch("notifier.core.feishu.urlopen") as opener:
        assert not send_feishu_notification(
            event("TaskCompleted", {"task_subject": "Run tests"}), environ=_webhook_env()
        )
    opener.assert_not_called()


def test_agent_completed_does_not_call_feishu_api():
    """Notification:agent_completed (background agent finished) makes no Feishu HTTP call."""
    with patch("notifier.core.feishu.urlopen") as opener:
        assert not send_feishu_notification(
            event("Notification", {"notification_type": "agent_completed"}), environ=_webhook_env()
        )
    opener.assert_not_called()


def test_stop_still_sends_feishu():
    """Stop (per-reply end) still alerts: no change to its semantics."""
    with patch("notifier.core.feishu.urlopen", return_value=FakeResponse({"code": 0})) as opener:
        assert send_feishu_notification(event("Stop"), environ=_webhook_env())
    assert opener.called
    sent = json.loads(opener.call_args.args[0].data.decode())
    assert "本轮回复结束" in sent["content"]["text"]


def test_permission_request_still_sends_feishu():
    """Human authorization requests still alert immediately."""
    with patch("notifier.core.feishu.urlopen", return_value=FakeResponse({"code": 0})) as opener:
        assert send_feishu_notification(event("PermissionRequest", {"tool_name": "Bash"}), environ=_webhook_env())
    assert opener.called


def test_waiting_input_events_still_send_feishu():
    """idle_prompt / agent_needs_input (waiting for human input) still alert."""
    for ntype in ("idle_prompt", "agent_needs_input"):
        with patch("notifier.core.feishu.urlopen", return_value=FakeResponse({"code": 0})) as opener:
            assert send_feishu_notification(
                event("Notification", {"notification_type": ntype}), environ=_webhook_env()
            )
        assert opener.called


def test_stop_failure_still_sends_feishu():
    """StopFailure (abnormal termination) still alerts."""
    with patch("notifier.core.feishu.urlopen", return_value=FakeResponse({"code": 0})) as opener:
        assert send_feishu_notification(
            event("StopFailure", {"error": "rate_limit"}), environ=_webhook_env()
        )
    assert opener.called


def test_permission_prompt_dedup_still_applies():
    """The delayed Notification:permission_prompt companion stays silenced (dedup unchanged)."""
    with patch("notifier.core.feishu.urlopen") as opener:
        assert not send_feishu_notification(
            event("Notification", {"notification_type": "permission_prompt"}), environ=_webhook_env()
        )
    opener.assert_not_called()


def test_timeout_raises_delivery_failure_not_crash():
    """A socket timeout must be a clean delivery failure (no exception leak)."""
    item = event("Stop")
    with patch("notifier.core.feishu.urlopen", side_effect=TimeoutError("timed out")):
        assert not send_feishu_notification(item, environ={
            "NOTIFIER_FEISHU_WEBHOOK": "https://open.feishu.cn/open-apis/bot/v2/hook/fake"
        })


class _FeishuMockServer:
    """Minimal local HTTP server acting as a Feishu group-robot endpoint."""

    def __init__(self, response_payload=b'{"code": 0, "msg": "success"}', status=200):
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer
        self.received = {}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                self.server.received["body"] = self.rfile.read(length)
                body = self.server.response_payload
                self.send_response(self.server.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        server.received = self.received
        server.response_payload = response_payload
        server.status = status
        self.server = server
        self.thread = threading.Thread(target=server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()
        return self.server.server_address[1]

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


def test_end_to_end_http_delivery_to_mock_endpoint():
    """Real HTTP stack: POST a Stop message to a local mock, success accepted."""
    from notifier.core import feishu

    mock = _FeishuMockServer()
    port = mock.start()
    try:
        url = f"http://127.0.0.1:{port}/open-apis/bot/v2/hook/fake"
        with patch.object(feishu, "_valid_webhook", return_value=True):
            assert send_feishu_notification(
                event("Stop"), environ={"NOTIFIER_FEISHU_WEBHOOK": url}
            )
    finally:
        mock.stop()
    sent = json.loads(mock.received["body"].decode())
    assert sent["msg_type"] == "text"
    assert "本轮回复结束" in sent["content"]["text"]
    assert "private-session" not in sent["content"]["text"]


def test_end_to_end_http_delivery_malformed_response_rejected():
    """Real HTTP stack: a non-JSON body from the endpoint is a clean rejection."""
    from notifier.core import feishu

    mock = _FeishuMockServer(response_payload=b"[]")
    port = mock.start()
    try:
        url = f"http://127.0.0.1:{port}/open-apis/bot/v2/hook/fake"
        with patch.object(feishu, "_valid_webhook", return_value=True):
            assert not send_feishu_notification(
                event("Stop"), environ={"NOTIFIER_FEISHU_WEBHOOK": url}
            )
    finally:
        mock.stop()

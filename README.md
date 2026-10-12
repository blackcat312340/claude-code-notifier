# Claude Code Notifier

Windows 托盘应用 — 当 Claude Code 需要你或任务完成时，立即收到桌面通知，无需盯着终端。

## 这是什么

Claude Code Notifier 是一个 Windows 原生的系统托盘工具，监听本地所有 Claude Code / Codex 项目的 hook 事件，将其转化为桌面通知。适合在后台跑 Claude Code 的开发者 — 切到别的窗口干别的事，Claude 完成了、需要授权了、卡住了，都能第一时间知道。

## 功能

- **桌面通知** — Claude Code 请求授权 / 等待输入 / 任务完成时弹窗提醒
- **系统托盘** — 后台静默运行，右键查看最近事件历史
- **不活跃检测** — Claude session 超过 5 分钟无响应自动提醒（计划中）
- **异常状态提醒** — 检测 hook 配置错误等异常模式（计划中）
- **中文优先** — 通知、菜单、详情均以中文显示
- **多项目监控** — 自动监听本机所有 Claude Code / Codex 项目

## 安装

```bash
# 安装依赖
pip install -e .

# 安装 hook 配置到 Claude Code / Codex
notifier-config
```

## 使用

```bash
# 启动后台托盘（静默运行，无控制台窗口）
pythonw -m notifier

# 或前台运行（显示日志）
python -m notifier
```

启动后，系统托盘会出现铃铛图标。当 Claude Code 触发 hook 事件时，Windows 通知会弹出。

## 要求

- Windows 10 / 11
- Python >= 3.12
- Claude Code 或 Codex CLI

## 技术栈

| 组件 | 技术 |
|------|------|
| 系统托盘 | pystray + Pillow |
| 桌面通知 | winotify (WinRT) |
| 事件通信 | 本地 TCP + NDJSON |
| IPC | asyncio socket server |
| Hook 入口 | Claude Code hooks → CLI → TCP |

## 架构

```
Claude/Codex hook 事件
    │
    ▼
CLI 入口 (notifier.cli.hook)
    │  classify → NDJSON
    ▼
TCP Server (localhost:47921)
    │  session registry + event dispatch
    ▼
通知分发 (notify worker thread)
    │  cooldown → winotify
    ▼
Windows 桌面通知
```

## 飞书跨电脑通知（无需服务器）

电脑 A 上的 Claude Code 通过 Hooks 将状态发送给飞书群机器人；电脑 B 只需登录同一飞书账号并加入该群。**无需在电脑 B 安装 Notifier。**

1. 在飞书新建群聊，进入群设置 → 群机器人 → 添加自定义机器人，保存其 Webhook 地址。
2. 如启用机器人「签名校验」，同时保存签名密钥。机器人安全策略还可能要求包含特定关键词；所有消息默认包含 `Claude Notifier`，可将其设为关键词。
3. 在 **运行 Claude Code 的同一个系统环境**（Windows 或 WSL）安装此项目，注册当前 Claude Hooks 并配置飞书：

```bash
python -m pip install -e .
notifier-config --skip-codex
notifier-feishu setup
notifier-feishu status
notifier-feishu test
```

`notifier-feishu setup` 会交互式输入 Webhook、可选签名密钥和设备名称。敏感信息仅保存于当前用户的 `~/.config/claude-code-notifier/feishu.json`，在 Linux/WSL 上设置为仅用户可读写（0600）；**切勿将该文件上传到 GitHub**。也可以改用环境变量：`NOTIFIER_FEISHU_WEBHOOK`、`NOTIFIER_FEISHU_SECRET`、`NOTIFIER_DEVICE_NAME`。环境变量优先。

4. 重启 Claude Code 并触发一次正常回复结束；也可运行 `notifier-feishu test` 立即检查飞书群是否收到消息。

发送的事件包括：`Stop`（**本轮回复结束，并非严格任务完成**）、`TaskCompleted`（明确标记某项任务完成）、`PermissionRequest`（请求授权）、`Notification` 的 `idle_prompt` / `agent_needs_input` / `agent_completed`、`StopFailure`（API 错误）。`SessionStart` 仍记录但不推送。

- 默认**不会**推送完整回复、工具输入、会话 ID、Transcript 路径及原始 Hook Payload。默认仅推送事件、项目名、设备名，以及允许的有限任务/错误字段。对话摘要需显式设置 `NOTIFIER_FEISHU_INCLUDE_MESSAGE=1`（注意可能泄露私密信息）。
- WSL/Linux 默认仅向飞书发送通知，不连接 Windows 托盘进程；设置 `NOTIFIER_LOCAL_TCP=1` 可强制启用原有本地 TCP。Windows 原有托盘通知继续工作。
- 每条飞书 HTTP 请求超时 3 秒；无网络或者机器人配置错误时仅记录最小错误类型，不改变 Claude 的权限控制或工作流。群机器人只支持群通知，不支持个人私聊。
- 请在飞书中设置消息提醒，电脑 B 才会弹出桌面通知。飞书的组织策略可能禁止添加自定义机器人。
- 安装器仅修改 `~/.claude/settings.json` 的 `hooks`，保留其他配置；反复运行不会重复添加同一个 notifier-owned Hook。

## 开发

```bash
git clone https://github.com/blackcat312340/claude-code-notifier.git
cd claude-code-notifier
pip install -e .\npython -m pip install pytest pytest-asyncio
pytest src/notifier/tests/ -v
```

## 许可证

MIT

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
notifier-config install
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

## 开发

```bash
git clone https://github.com/blackcat312340/claude-code-notifier.git
cd claude-code-notifier
pip install -e ".[dev]"
pytest src/notifier/tests/ -v
```

## 许可证

MIT

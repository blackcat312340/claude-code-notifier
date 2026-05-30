# Feature Research

## Core User Jobs

- Know when Claude Code is waiting for the developer
- Know when Claude Code has reached a natural stopping point
- Know when Claude Code appears stuck or abnormal
- Avoid living in the terminal just to monitor progress

## Table Stakes for v1

### Hook Integration

- Install supported hook commands into Claude Code user settings
- Receive structured hook payloads with session and project context
- Distinguish event classes such as notification, stop, and session lifecycle events

### Notificationing

- Trigger Windows desktop notifications
- Label reminders by type
- Include enough context to identify which project needs attention

### Session Awareness

- Track local Claude sessions by `session_id`
- Associate sessions with project directories
- Keep a recent event timeline for debugging and trust

### Operator Surface

- Background tray process status
- Recent reminder list
- Basic controls such as pause notifications, open logs, install hooks, uninstall hooks

## Likely Differentiators After v1

- Remote channels such as Telegram or WeChat
- Smarter summarization of why intervention is needed
- Click-through back into the relevant project or session
- Per-project rule tuning and quiet hours

---
*Last updated: 2026-05-29*

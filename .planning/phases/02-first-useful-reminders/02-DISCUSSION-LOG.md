# Phase 2: First Useful Reminders - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-30
**Phase:** 02-first-useful-reminders
**Areas discussed:** Tray & notification stack, Notification rules, Process architecture, Tray menu behavior

---

## Tray & Notification Stack

| Option | Description | Selected |
|--------|-------------|----------|
| pystray | Cross-platform tray library, simple API, Pillow icons | ✓ |
| win32gui + infi.systray | Windows-only native integration, more control | |
| Custom tkinter/threading | Zero deps, maximum control, more code | |

| Option | Description | Selected |
|--------|-------------|----------|
| winotify | Modern WinRT toasts, title+body+icon, clean API | ✓ |
| win10toast-py | Simpler API, battle-tested, less feature-rich | |
| plyer | Cross-platform facade, less Windows-native | |

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal placeholder | Simple built-in icon, no custom design | ✓ |
| Claude-branded icon | Anthropic/Claude logo for brand recognition | |
| Custom notifier icon | Bell or notification dot, needs .ico file | |

| Option | Description | Selected |
|--------|-------------|----------|
| Title + body | Project name title, reminder type + context body | ✓ |
| Title + type only | Minimal format, satisfies ATTN-03 only | |
| With action buttons | Action buttons for future navigation | |

---

## Notification Rules

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — notify DONE | PERMISSION + IDLE + DONE, core value delivery | ✓ |
| No — only PERMISSION + IDLE | Sparse, signal-rich notifications | |
| All 4 categories | Maximum visibility, risk of fatigue | |

| Option | Description | Selected |
|--------|-------------|----------|
| 30s cooldown | Per (project, category) key, simple and predictable | ✓ |
| No cooldown | Every event produces notification | |
| Once per session | One notification per session per category | |

| Option | Description | Selected |
|--------|-------------|----------|
| Log only | Log ERROR events, don't notify | ✓ |
| Notify ERROR too | User should know if something is broken | |
| Drop silently | Only handle actionable events | |

| Option | Description | Selected |
|--------|-------------|----------|
| No click action | Dismiss on click, defer to Phase 3+ | ✓ |
| Open project folder | Open File Explorer at project cwd | |
| Open tray status | Bring tray to foreground | |

---

## Process Architecture

| Option | Description | Selected |
|--------|-------------|----------|
| python -m notifier | Single command launches tray app | ✓ |
| Separate entry point | notifier-tray or notifier-daemon | |
| Single entry with --tray flag | python -m notifier --tray | |

| Option | Description | Selected |
|--------|-------------|----------|
| Threaded (TCP in daemon thread) | pystray owns main thread, asyncio in background | ✓ |
| Async main + pystray thread | asyncio in main, pystray in thread | |
| Threaded socketserver | Replace asyncio entirely with threaded server | |

| Option | Description | Selected |
|--------|-------------|----------|
| Silent | No console window, .pyw or pythonw.exe | ✓ |
| Console then minimize | Console visible initially, minimized after tray | |
| Show console | Console with log output, debugging-friendly | |

| Option | Description | Selected |
|--------|-------------|----------|
| Manual start only | User runs python -m notifier when needed | ✓ |
| Opt-in auto-start | --install-startup flag in notifier-config | |
| Auto-start by default | Always-on, matches monitoring vision | |

---

## Tray Menu Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Exit only | Single "Exit" menu item | ✓ |
| Status + Exit | Monitoring status + project count + Exit | |
| Status + recent events + Exit | Quick glance at last 3 events | |

| Option | Description | Selected |
|--------|-------------|----------|
| Status with session count | Live count of active sessions | ✓ |
| Static name only | "Claude Code Notifier" | |
| Last event live | Most recent event with timestamp | |

---

## Claude's Discretion

No areas deferred to Claude — all decisions explicitly captured by the user.

## Deferred Ideas

None — discussion stayed within Phase 2 scope.

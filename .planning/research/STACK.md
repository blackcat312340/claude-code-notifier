# Stack Research

## Goal

Identify a pragmatic Windows-first implementation stack for a local Claude Code notifier built around official hooks.

## Recommended Direction

- **Runtime**: Python 3.11+ for fast iteration, local tooling familiarity, and strong Windows support
- **Tray/App Shell**: A lightweight desktop/tray layer such as `pystray` or a small Qt-based shell if richer UI becomes necessary
- **Notifications**: Native Windows toast support through a maintained Python library or Windows app notification bridge
- **Persistence**: Small local SQLite or JSON event store for recent events and session heartbeat state
- **Hook Runner**: A CLI entrypoint that Claude Code invokes from `~/.claude/settings.json`

## Why This Fits

Python keeps the first release simple in a repository that is already positioned as a Python workspace. A notifier tool mostly needs local I/O, event parsing, background state management, and packaging rather than heavy rendering or distributed systems infrastructure.

## Risks

- Some tray libraries are minimal and awkward on Windows for richer menus or settings
- Native Windows toast packaging can be annoying if the app identity is not handled cleanly
- If hook commands need to return very quickly, any heavy logic should be handed off to a long-running background process

## Decision Pressure

Prototype with a simple Python tray process first. Revisit the shell technology only if packaging or Windows notification quality becomes a blocker.

---
*Source basis: official Claude Code hooks docs + local project context*

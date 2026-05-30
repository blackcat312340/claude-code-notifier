# Research Summary

## Stack

Use a Windows-first Python desktop utility with a small resident tray/background process and a lightweight hook CLI entrypoint.

## Table Stakes

- Official Claude Code hook integration
- Reliable Windows desktop notifications
- Session/project identification
- Recent event visibility
- Safe install/uninstall of user-level hook configuration

## Watch Out For

- Hook latency and overwork in synchronous paths
- Destructive edits to `~/.claude/settings.json`
- Noisy inactivity heuristics
- Packaging gaps that break Windows notifications

## Product Implication

The MVP should center on a clean hook-to-event pipeline first. A notifier that cannot reliably ingest and classify Claude events will fail even if the tray UI looks polished.

---
*Last updated: 2026-05-29*

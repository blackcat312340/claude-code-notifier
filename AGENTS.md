# AGENTS

## Project

Claude Code Notifier is a Windows-first tray application that listens to official Claude Code hooks and reminds the developer when Claude needs attention, becomes idle, or appears abnormal.

## Working Rules

- Follow GSD workflow artifacts in `.planning/`
- Treat `.planning/PROJECT.md` as the source of truth for scope and constraints
- Treat `.planning/REQUIREMENTS.md` as the definition of done
- Treat `.planning/ROADMAP.md` as the phase map
- Prefer supported Claude Code hook integration over terminal scraping
- Keep hook execution lightweight; push heavier work to a resident notifier process

## Current Focus

- Current phase: Phase 1 - Hook Event Backbone
- Next workflow step: `gsd-discuss-phase 1`

## Key Files

- `.planning/PROJECT.md`
- `.planning/config.json`
- `.planning/research/SUMMARY.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/STATE.md`

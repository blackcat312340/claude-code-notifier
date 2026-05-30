# Claude Code Notifier

## What This Is

Claude Code Notifier is a Windows-first tray application that listens to Claude Code hook events and turns them into user-facing reminders. It is for developers who run Claude Code locally and want immediate notification when Claude finishes a task, needs human input, hits an abnormal state, or appears stalled.

## Core Value

When Claude Code needs you or finishes waiting for you, you should know immediately without watching the terminal.

## Requirements

### Validated

(None yet - ship to validate)

### Active

- [ ] Detect Claude Code hook events across local projects and normalize them into notifier events
- [ ] Show Windows desktop notifications for completion, intervention-needed, error-like, and inactivity signals
- [ ] Provide a tray-based control surface for recent session state and notifier status
- [ ] Install and uninstall Claude Code hook configuration at the user level

### Out of Scope

- Mobile or web companion clients - not needed for the first local utility release
- Remote push channels such as WeChat, Telegram, or email - defer until local desktop notifications prove useful
- Deep Claude transcript inspection or a full session viewer - not required to validate the reminder workflow
- Automatic permission approval or task control over Claude Code - the tool should notify, not take over execution

## Context

The tool is intended to monitor all Claude Code projects on the current machine, not just one repository. The preferred integration path is Claude Code's official hooks system, especially `Notification`, `Stop`, `SessionStart`, and related events, because it gives a supported entry point without terminal scraping. Official hook docs show that hooks can be installed in `~/.claude/settings.json`, receive JSON over stdin, and expose session metadata such as `session_id`, `transcript_path`, `cwd`, and event-specific payloads.

The first release is Windows-first. That implies native desktop notification support, a background tray process, and a packaging story that does not require users to hand-edit Claude settings. The product needs a lightweight event pipeline that can map hook payloads to project names and reminder categories, while also adding an inactivity detector for cases not covered directly by hook notifications.

The user-defined intervention examples are:

- Claude asks for permission to use a tool or run a command
- Tests fail and the developer needs to choose a fix direction
- Required environment variables or secrets are missing
- Claude needs a product or implementation decision before continuing

## Constraints

- **Platform**: Windows first, but architecture should leave room for future macOS/Linux support
- **Integration**: Use official Claude Code hooks as the primary event source - avoid brittle terminal scraping for v1
- **Scope**: Monitor all Claude Code projects on the local machine - no per-project opt-in for v1
- **Notification Channel**: Desktop notifications only for v1 - keep delivery local and reliable
- **UX**: Desktop notification click actions are not required in v1 - reminder quality matters more than deep navigation
- **Workflow**: Plan with GSD using vertical MVP phases - each phase should deliver observable user value

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use Claude Code hooks as the integration backbone | Officially supported, structured JSON payloads, avoids parsing terminal output | Pending |
| Build a tray application instead of a pure CLI daemon | User wants an always-on reminder tool with visible background presence | Pending |
| Treat `idle_prompt`-style waiting as a completion/waiting reminder in v1 | Matches the user's definition of "task complete enough to notify" | Pending |
| Monitor all local Claude Code projects by default | Reduces setup friction and matches the stated monitoring scope | Pending |
| Keep notification content concise: project name plus reminder type | Satisfies the desired signal level without forcing transcript parsing into every notification | Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition**:
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone**:
1. Full review of all sections
2. Core Value check - still the right priority?
3. Audit Out of Scope - reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-29 after initialization*

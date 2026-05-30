# Pitfalls Research

## 1. Overloading Hook Execution

**Warning signs**

- Hook commands feel slow
- Claude Code waits noticeably after events
- Notifications arrive late or not at all

**Prevention**

- Keep hook commands minimal
- Forward work to a resident background process
- Add logging around hook execution latency

**Phase**

Phase 1

## 2. Clobbering Existing Claude Settings

**Warning signs**

- Hook installer rewrites unrelated settings
- User loses previous hook configuration
- Uninstall cannot restore a clean prior state

**Prevention**

- Merge settings carefully
- Back up prior hook config
- Make install/uninstall reversible and idempotent

**Phase**

Phase 2

## 3. False Positives for "Stuck" Detection

**Warning signs**

- Users get inactivity notifications during normal long-running work
- Developers disable the notifier due to noise

**Prevention**

- Start with a conservative threshold
- Scope inactivity to known active sessions
- Deduplicate repeated alerts

**Phase**

Phase 4

## 4. Weak Project Identification

**Warning signs**

- Notifications do not clearly identify which repo needs attention
- Multiple sessions become indistinguishable

**Prevention**

- Prefer project directory metadata from hook payloads
- Normalize display names consistently
- Track session-to-project mapping explicitly

**Phase**

Phase 1

## 5. Windows Packaging Friction

**Warning signs**

- Notifications work only in dev mode
- Tray app behaves differently after packaging
- Install instructions become too manual

**Prevention**

- Test notifications in packaged form early
- Keep runtime dependencies modest
- Separate packaging validation from feature logic

**Phase**

Phase 5

---
*Last updated: 2026-05-29*

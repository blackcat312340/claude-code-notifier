---
phase: 04
slug: abnormal-state-detection
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-04
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (existing project) |
| **Config file** | `pyproject.toml` (existing `[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest src/notifier/tests/ -x --timeout=30` |
| **Full suite command** | `pytest src/notifier/tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest src/notifier/tests/ -x --timeout=30`
- **After every plan wave:** Run `pytest src/notifier/tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | ANOM-01 | N/A | Polling loop reads last_seen, no external network | unit | `pytest src/notifier/tests/test_inactivity.py -k test_polling` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | ANOM-01 | N/A | Inactivity timer thread isolation | unit | `pytest src/notifier/tests/test_inactivity.py -k test_timer` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | ANOM-03 | N/A | Cooldown prevents duplicate inactivity notifications | unit | `pytest src/notifier/tests/test_inactivity.py -k test_cooldown` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 1 | ANOM-02 | N/A | ERROR flood threshold (3/2min) detection | unit | `pytest src/notifier/tests/test_flood.py -k test_flood` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 1 | ANOM-02 | N/A | Flood notification cooldown (10min) | unit | `pytest src/notifier/tests/test_flood.py -k test_flood_cooldown` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/notifier/tests/test_inactivity.py` — stubs for ANOM-01, ANOM-03 (inactivity detection + cooldown)
- [ ] `src/notifier/tests/test_flood.py` — stubs for ANOM-02 (ERROR flood detection)
- [ ] `src/notifier/tests/conftest.py` — existing, may need SessionRecord fixture extensions with `is_stopped`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Desktop notification appears on 5min inactivity | ANOM-01 | winotify requires Windows toast infrastructure; can't assert in headless CI | Run notifier, wait 5min without events, verify toast appears with "疑似卡住" text |
| Tray tooltip updates after inactivity detection | ANOM-01 | pystray GUI requires visible desktop | Right-click tray, verify menu shows inactivity events in history |
| ERROR flood notification appears | ANOM-02 | winotify toast — same reason as above | Inject rapid ERROR events via test hook CLI, verify flood notification within 2min |
| Chinese notification copy is correct | ANOM-01, ANOM-02 | Visual verification of rendered text | Inspect notification body text for expected Chinese phrases |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

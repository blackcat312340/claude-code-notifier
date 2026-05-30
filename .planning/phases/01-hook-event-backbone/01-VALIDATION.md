---
phase: 01
slug: hook-event-backbone
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-30
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none yet — add `pyproject.toml [tool.pytest.ini_options]` |
| **Quick run command** | `pytest -x src/notifier/tests/ -q --tb=short` |
| **Full suite command** | `pytest src/notifier/tests/ -v --tb=short` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest -x src/notifier/tests/ -q --tb=short`
- **After every plan wave:** Run `pytest src/notifier/tests/ -v --tb=short`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | HOOK-01 | T-01-01 | Deep-merge preserves unrelated keys | unit | `pytest src/notifier/tests/test_settings.py::test_install_hooks_preserves_existing -x` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | HOOK-03 | T-01-02 | JSON stdin parsed safely, forwarded to TCP | integration | `pytest src/notifier/tests/test_cli_hook.py::test_forward_event -x` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 1 | SESS-01 | — | Composite key uniqueness enforced | unit | `pytest src/notifier/tests/test_session.py::test_composite_key -x` | ❌ W0 | ⬜ pending |
| 01-01-04 | 01 | 1 | SESS-02 | — | Leaf dir extraction from Windows paths | unit | `pytest src/notifier/tests/test_session.py::test_project_name_from_cwd -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/notifier/tests/` — directory + `__init__.py` + `conftest.py`
- [ ] `src/notifier/tests/test_settings.py` — covers HOOK-01 (deep-merge hooks, preserve unrelated settings)
- [ ] `src/notifier/tests/test_cli_hook.py` — covers HOOK-03 (stdin JSON → TCP forward with retry)
- [ ] `src/notifier/tests/test_session.py` — covers SESS-01 (composite key), SESS-02 (project name from cwd)
- [ ] `src/notifier/tests/test_events.py` — covers event classification (permission/idle/done/error)
- [ ] `src/notifier/tests/test_ipc.py` — covers TCP send with retry and backoff
- [ ] `pyproject.toml` pytest config (`[tool.pytest.ini_options]`)
- [ ] `pip install pytest` — if none detected

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Hook installation into live ~/.claude/settings.json | HOOK-01 | Destructive test on real user config | Backup settings.json, run `notifier-config install`, verify hooks added without data loss, restore backup |
| End-to-end hook event from Claude Code to notifier | HOOK-03 | Requires running Claude Code session | Start notifier, trigger a Claude Code session, verify event appears in notifier log |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

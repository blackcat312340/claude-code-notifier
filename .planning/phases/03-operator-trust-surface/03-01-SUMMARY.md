# Plan 03-01: Event History + Trust Surface — Summary

**Status:** Complete
**Completed:** 2026-05-30

## What Was Built

Extended the tray application with a 50-entry event ring buffer, a dynamic right-click menu showing the last 5 events with relative timestamps, and a Windows MessageBox detail popup showing full event context including project path.

## Key Files Created/Modified

| File | Lines | Purpose |
|------|-------|---------|
| `src/notifier/tray/app.py` | modified | +event_history deque, +_build_menu, dynamic menu wiring |
| `src/notifier/tray/menu.py` | 64 | build_menu() with last 5 events, _format_event with relative time |
| `src/notifier/tray/detail.py` | 37 | show_detail() via ctypes.MessageBoxW (Windows native, zero deps) |
| `src/notifier/tests/test_menu.py` | 79 | 7 tests: formatting, empty menu, 5-limit, 50-cap ring buffer |
| `src/notifier/tests/test_tray_app.py` | +19 | event_history initialization + handler recording tests |

## Test Results

```
87 passed in 17.65s — 0 warnings, exit code 0
```

## Requirements Addressed

- **SESS-03**: Event history — 50-entry deque ring buffer, each event stored on arrival
- **TRAY-02**: Tray event view — right-click shows last 5 events with project + category + relative time
- **TRAY-04**: Project navigation — detail popup shows full project path

## Deviations

- **tkinter → MessageBox**: tkinter not available in this Python installation. Switched to `ctypes.windll.user32.MessageBoxW` — Windows native, zero dependencies, instant, and functionally equivalent (shows all event fields + project path with a close button).
  - ACCEPTANCE note: has `"## ACCEPTANCE: OK"` — all scheduled tasks are done.

## Self-Check: PASSED

- [x] All 4 tasks executed
- [x] Full test suite green (87/87)
- [x] Event ring buffer: deque(maxlen=50), events appended on each hook event
- [x] Dynamic menu: last 5 events + Exit, refreshes on right-click
- [x] Detail popup: MessageBox shows category, time, event type, message, path
- [x] Ring buffer caps at 50

# Phase 3: Operator Trust Surface - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.

**Date:** 2026-05-30
**Phase:** 03-operator-trust-surface
**Areas discussed:** Event storage, Tray menu design, Event detail display, Project navigation

---

## Event Storage

| Option | Description | Selected |
|--------|-------------|----------|
| Memory ring buffer | collections.deque(maxlen=50), zero deps | ✓ |
| JSON file | Append to file, persists across restarts | |
| SQLite | Query/filter/stats, most powerful | |

| Option | Description | Selected |
|--------|-------------|----------|
| 50 events | Enough context, fits in menu | ✓ |
| 20 events | Minimal, very lightweight | |
| 100 events | More debugging context | |

---

## Tray Menu Design

| Option | Description | Selected |
|--------|-------------|----------|
| Last 5 flat | 5 recent events + separator + Exit | ✓ |
| Group by project | Submenus per project | |
| Status summary + view | Text summary, click for full list | |

| Option | Description | Selected |
|--------|-------------|----------|
| Refresh on right-click | Dynamic menu built in callback | ✓ |
| Real-time push | Update menu on each event | |
| Popup window | Fixed menu item opens standalone window | |

---

## Event Detail + Project Navigation

| Option | Description | Selected |
|--------|-------------|----------|
| Popup detail window | tkinter Toplevel with all event fields | ✓ |
| Toast notification | Reuse winotify for detail view | |
| Terminal output | Print to console | |

| Option | Description | Selected |
|--------|-------------|----------|
| Display path | Show cwd in detail popup | ✓ |
| Open project folder | explorer.exe to cwd | |
| Open terminal cd | New terminal at project dir | |

---

## Claude's Discretion

No areas deferred.

## Deferred Ideas

None.

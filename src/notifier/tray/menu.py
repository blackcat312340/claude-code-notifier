"""Dynamic tray menu builder — reads event history, builds pystray menu."""
from datetime import datetime, timezone
from notifier.tray.detail import show_detail


def _format_event(event, index):
    """Format one event as a menu item label.

    Returns (label, event) tuple. Label format: "project - category (N mins ago)"
    """
    project = event.session.project_name
    cat = event.category.value if hasattr(event.category, 'value') else str(event.category)

    # Relative time
    try:
        ts = datetime.fromisoformat(event.timestamp)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - ts
        mins = int(delta.total_seconds() / 60)
        if mins < 1:
            ago = "just now"
        elif mins == 1:
            ago = "1 min ago"
        else:
            ago = f"{mins} mins ago"
    except Exception:
        ago = ""

    label = f"{project} - {cat}"
    if ago:
        label += f" ({ago})"
    return label, event


def build_menu(tray):
    """Build a dynamic pystray menu with last 5 events + Exit.

    Per D-03: 5 most recent events at top, separator, then Exit.
    Per D-04: Called on every right-click — always shows current state.

    Args:
        tray: NotifierTray instance with event_history, shutdown()
    """
    import pystray

    items = []

    # Show up to 5 most recent events
    for i, event in enumerate(tray.event_history):
        if i >= 5:
            break
        label, ev = _format_event(event, i)
        # Use a factory function to capture `ev` in closure
        def _make_action(e):
            def action(icon, item):
                show_detail(e)
            return action
        items.append(pystray.MenuItem(label, _make_action(ev)))

    if items:
        items.append(pystray.Menu.SEPARATOR)
    else:
        items.append(pystray.MenuItem(
            "No events yet", lambda icon, item: None,
        ))
        items.append(pystray.Menu.SEPARATOR)

    items.append(
        pystray.MenuItem(
            "Exit",
            lambda icon, item: tray.shutdown(icon),
        )
    )

    return pystray.Menu(*items)

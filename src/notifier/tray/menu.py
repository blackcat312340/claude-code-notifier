"""Dynamic tray menu builder — reads event history, builds pystray menu."""
from notifier.tray.detail import show_detail
from notifier.core.text import event_menu_label, relative_time_cn


def _format_event(event, index):
    """Format one event as a menu item label.

    Returns (label, event) tuple.
    Per D-02, D-11: provider source visible, Chinese-first labels.
    Format: "{provider} - {category} - {cn_label} ({relative_time})"
    """
    relative_time = relative_time_cn(event.timestamp)
    label = event_menu_label(event, relative_time=relative_time)
    return label, event


def build_menu(tray):
    """Build a dynamic pystray menu with last 5 events + Exit.

    Per D-03: 5 most recent events at top, separator, then Exit.
    Per D-04: Called on every right-click — always shows current state.
    Per D-11, D-12: Chinese-first labels (暂无事件, 退出).

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
            "暂无事件", lambda icon, item: None,
        ))
        items.append(pystray.Menu.SEPARATOR)

    items.append(
        pystray.MenuItem(
            "退出",
            lambda icon, item: tray.shutdown(icon),
        )
    )

    return pystray.Menu(*items)

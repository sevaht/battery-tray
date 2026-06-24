"""The battery-selection window."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from sevaht_gui import LabelGrooveFrame

from .battery import status_lines
from .config import MAX_POLL_SECONDS, MIN_POLL_SECONDS

if TYPE_CHECKING:
    from collections.abc import Callable

    from sevaht_gui import TkApp

    from .battery import BatteryStatus


class BatterySelectorWindow:
    """Lets the user pick which battery to monitor and shows its status.

    Built on the app's root window; the app drives :meth:`set_batteries` /
    :meth:`set_status` from its poll, and :meth:`show` from the tray.
    """

    def __init__(
        self,
        app: TkApp,
        *,
        on_select: Callable[[str], None],
        on_poll_change: Callable[[float], None],
        has_tray: bool,
    ) -> None:
        self.app = app
        self.root = app.root
        self._on_select = on_select
        self._on_poll_change = on_poll_change
        self._has_tray = has_tray
        self._battery_var = tk.StringVar(master=self.root)
        self._poll_var = tk.StringVar(master=self.root)
        self._build_ui()

    def _build_ui(self) -> None:
        self.root.title("Battery Tray")
        self.root.resizable(False, False)
        self.root.minsize(260, 0)

        content = ttk.Frame(self.root, padding=16)
        content.pack(fill=tk.BOTH, expand=True)

        box = LabelGrooveFrame(content, text="Battery")
        box.pack(fill=tk.X)

        self._combo = ttk.Combobox(
            box.interior,
            textvariable=self._battery_var,
            state="readonly",
            width=24,
        )
        self._combo.pack(fill=tk.X, padx=6, pady=(0, 8))
        self._combo.bind("<<ComboboxSelected>>", self._on_combo_selected)

        self._status_label = ttk.Label(box.interior, justify=tk.LEFT, text="")
        self._status_label.pack(anchor="w", padx=6, pady=(0, 4))

        settings = LabelGrooveFrame(content, text="Settings")
        settings.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(settings.interior, text="Refresh every (seconds):").pack(
            side=tk.LEFT, padx=(6, 6)
        )
        poll_spinbox = ttk.Spinbox(
            settings.interior,
            textvariable=self._poll_var,
            from_=MIN_POLL_SECONDS,
            to=MAX_POLL_SECONDS,
            increment=1,
            width=7,
            command=self._on_poll_committed,
        )
        poll_spinbox.pack(side=tk.LEFT, padx=(0, 6))
        # Commit on spin (command), on Enter, and on leaving the field.
        poll_spinbox.bind("<Return>", self._on_poll_committed)
        poll_spinbox.bind("<FocusOut>", self._on_poll_committed)

        buttons = ttk.Frame(content)
        buttons.pack(fill=tk.X, pady=(12, 0))
        # The window-close (X) is handled by TkApp: hide when a tray houses the
        # window, quit otherwise.
        if self._has_tray:
            ttk.Button(buttons, text="Hide", command=self.app.hide).pack(
                side=tk.RIGHT
            )
        ttk.Button(buttons, text="Quit", command=self.app.quit).pack(
            side=tk.RIGHT, padx=(0, 6) if self._has_tray else (0, 0)
        )

    def _on_combo_selected(self, _event: tk.Event[ttk.Combobox]) -> None:
        name = self._battery_var.get()
        if name:
            self._on_select(name)

    def _on_poll_committed(
        self, _event: tk.Event[ttk.Spinbox] | None = None
    ) -> None:
        try:
            seconds = float(self._poll_var.get())
        except ValueError:
            return  # leave the field as-is so the user can correct it
        seconds = max(MIN_POLL_SECONDS, min(seconds, MAX_POLL_SECONDS))
        self.set_poll_seconds(seconds)
        self._on_poll_change(seconds)

    def set_poll_seconds(self, seconds: float) -> None:
        """Show the current refresh interval (UI thread)."""
        self._poll_var.set(f"{seconds:g}")

    def set_batteries(self, names: list[str], selected: str | None) -> None:
        """Update the battery choices and the current selection (UI thread)."""
        self._combo["values"] = names
        if selected is not None and selected in names:
            self._battery_var.set(selected)
        else:
            self._battery_var.set(names[0] if names else "")

    def set_status(self, status: BatteryStatus | None) -> None:
        """Update the shown status for the selected battery (UI thread)."""
        if status is None:
            self.root.title("Battery Tray - No battery")
            self._status_label.configure(text="No battery detected.")
            return
        charge_state = "charging" if status.charging else "discharging"
        self.root.title(f"Battery Tray - {status.capacity}% ({charge_state})")
        self._status_label.configure(text="\n".join(status_lines(status)))

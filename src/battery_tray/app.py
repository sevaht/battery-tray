"""Wires the tray icon, selection window, and battery polling together."""

from __future__ import annotations

import contextlib
import logging
from tkinter import TclError
from typing import TYPE_CHECKING

from sevaht_gui import TkApp

from . import APP_NAME, CONFIG_FILE_NAME, user_config_path
from .battery import list_batteries, read_battery, status_lines
from .config import clamp_poll_seconds, load_config, save_config
from .render import IconStyle, battery_renderer
from .window import BatterySelectorWindow

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from PIL import Image

    from .battery import BatteryStatus

logger = logging.getLogger(__name__)

# Charge buckets (every 5%) at which the icon is re-rendered; finer changes do
# not visibly alter the icon.
_ICON_BUCKET = 5


class BatteryTray:
    def __init__(
        self,
        config_path: Path | None = None,
        *,
        style: IconStyle | None = None,
    ) -> None:
        self.config_path = config_path or user_config_path() / CONFIG_FILE_NAME
        self.style = style or IconStyle()
        self._config = load_config(self.config_path)
        self.poll_ms = int(self._config.poll_seconds * 1000)

        self._batteries = list_batteries()
        self._selected = self._initial_selection()
        self._status: BatteryStatus | None = (
            read_battery(self._selected) if self._selected else None
        )
        self._icon_key = self._current_icon_key()
        self._notified_level = self._status.level if self._status else None
        self._notified_charging = (
            self._status.charging if self._status else None
        )
        self._poll_after: str | None = None

        # TkApp defaults handle theme, centering/position, quit confirmation,
        # the window icon (matched to the tray icon), and window-close behavior.
        self.app = TkApp()
        self.tray_icon = self.app.create_tray_icon(
            APP_NAME,
            self._tooltip(),
            self._render(),
            activate_label="Configure...",
        )
        self.window = BatterySelectorWindow(
            self.app,
            on_select=self._on_select,
            on_poll_change=self._on_poll_change,
            has_tray=self.app.has_tray,
        )
        self.window.set_batteries(self._batteries, self._selected)
        self.window.set_poll_seconds(self._config.poll_seconds)
        self.window.set_status(self._status)

    def _initial_selection(self) -> str | None:
        saved = self._config.battery
        if saved is not None and saved in self._batteries:
            return saved
        return self._batteries[0] if self._batteries else None

    def _current_icon_key(self) -> tuple[int, bool] | None:
        if self._status is None:
            return None
        return (self._status.capacity // _ICON_BUCKET, self._status.charging)

    def _render(self) -> Callable[[int], Image.Image]:
        percent = self._status.capacity if self._status else 0
        connected = self._status.charging if self._status else False
        return battery_renderer(percent, connected=connected, style=self.style)

    def _tooltip(self) -> str:
        if self._status is None:
            return "Battery Tray\nNo battery"
        # First line is the header; the rest render as the tooltip body
        # (multiline where the tray host supports it).
        return f"{self._status.name}\n" + "\n".join(status_lines(self._status))

    def _on_select(self, name: str) -> None:
        self._selected = name
        self._config.battery = name
        save_config(self.config_path, self._config)
        self._refresh()

    def _on_poll_change(self, seconds: float) -> None:
        seconds = clamp_poll_seconds(seconds)
        self.poll_ms = int(seconds * 1000)
        self._config.poll_seconds = seconds
        save_config(self.config_path, self._config)
        self._schedule_poll()

    def _refresh(self) -> None:
        # Runs on the UI thread (poll timer or a window callback).
        batteries = list_batteries()
        if batteries != self._batteries:
            self._batteries = batteries
            if self._selected not in batteries:
                self._selected = batteries[0] if batteries else None
            self.window.set_batteries(batteries, self._selected)
        self._status = read_battery(self._selected) if self._selected else None
        self._apply_status()
        self.window.set_status(self._status)
        self._maybe_notify()

    def _apply_status(self) -> None:
        # Push the current status to the tray tooltip and to both the tray and
        # window icons (set_app_icon keeps them in sync).
        if self.tray_icon is not None:
            self.tray_icon.title = self._tooltip()
        key = self._current_icon_key()
        if key != self._icon_key:
            self.app.set_app_icon(self._render())
            self._icon_key = key

    def _maybe_notify(self) -> None:
        status = self._status
        if status is None:
            return
        if (
            status.level == self._notified_level
            and status.charging == self._notified_charging
        ):
            return
        # app.notify uses the tray when present and falls back to a standalone
        # notifier otherwise -- no need to handle the no-tray case here.
        self.app.notify(
            f"Battery - {status.level.name.title()}",
            "\n".join(status_lines(status)),
            icon=status.level.value,
        )
        self._notified_level = status.level
        self._notified_charging = status.charging

    def _schedule_poll(self) -> None:
        if self._poll_after is not None:
            with contextlib.suppress(TclError):
                self.app.root.after_cancel(self._poll_after)
        self._poll_after = self.app.root.after(self.poll_ms, self._poll)

    def _poll(self) -> None:
        self._refresh()
        self._poll_after = self.app.root.after(self.poll_ms, self._poll)

    def run(self, *, start_hidden: bool = True) -> int:
        self._schedule_poll()
        self.app.run(self.tray_icon, start_hidden=start_hidden)
        return 0

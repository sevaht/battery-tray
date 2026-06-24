from __future__ import annotations

from typing import TYPE_CHECKING

from battery_tray.config import (
    DEFAULT_POLL_SECONDS,
    MAX_POLL_SECONDS,
    Config,
    load_config,
    save_config,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_load_missing_returns_defaults(tmp_path: Path) -> None:
    config = load_config(tmp_path / "config.json")
    assert config.battery is None
    assert config.poll_seconds == DEFAULT_POLL_SECONDS


def test_save_then_load_roundtrip(tmp_path: Path) -> None:
    # Parent dir does not exist yet; save should create it.
    path = tmp_path / "sevaht" / "battery-tray" / "config.json"
    save_config(path, Config(battery="BAT0", poll_seconds=10.0))
    loaded = load_config(path)
    assert loaded.battery == "BAT0"
    assert loaded.poll_seconds == 10.0


def test_load_ignores_garbage(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("not json", encoding="utf-8")
    assert load_config(path).battery is None


def test_poll_seconds_clamped_on_load(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    save_config(path, Config(poll_seconds=99999.0))
    assert load_config(path).poll_seconds == MAX_POLL_SECONDS

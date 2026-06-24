"""Persisting battery-tray settings to a small JSON config file."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_POLL_SECONDS = 5.0
MIN_POLL_SECONDS = 1.0
MAX_POLL_SECONDS = 3600.0


def clamp_poll_seconds(seconds: float) -> float:
    return max(MIN_POLL_SECONDS, min(seconds, MAX_POLL_SECONDS))


@dataclass
class Config:
    battery: str | None = None
    poll_seconds: float = DEFAULT_POLL_SECONDS


def load_config(config_path: Path) -> Config:
    """Load settings, falling back to defaults for anything missing/invalid."""
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Config()
    if not isinstance(data, dict):
        return Config()
    battery = data.get("battery")
    if not isinstance(battery, str):
        battery = None
    poll = data.get("poll_seconds")
    poll_seconds = (
        clamp_poll_seconds(float(poll))
        if isinstance(poll, (int, float)) and not isinstance(poll, bool)
        else DEFAULT_POLL_SECONDS
    )
    return Config(battery=battery, poll_seconds=poll_seconds)


def save_config(config_path: Path, config: Config) -> None:
    """Persist settings, creating the config directory if needed."""
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(
                {
                    "battery": config.battery,
                    "poll_seconds": config.poll_seconds,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    except OSError:
        logger.warning("Could not save config", exc_info=True)

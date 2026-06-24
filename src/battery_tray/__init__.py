"""A system-tray battery monitor built on sevaht-gui.

Attributes:
    __version__: The installed distribution version.
"""

from __future__ import annotations

import importlib.metadata
from functools import cache
from typing import TYPE_CHECKING

from platformdirs import PlatformDirs

if TYPE_CHECKING:
    from pathlib import Path

__version__ = importlib.metadata.version(__package__)

APP_NAME = "battery-tray"
APP_AUTHOR = "sevaht"
CONFIG_FILE_NAME = "config.json"


@cache
def user_config_path() -> Path:
    """Return the per-user config directory (``<author>/<appname>``)."""
    path = PlatformDirs(APP_NAME, appauthor=APP_AUTHOR).user_config_path
    # platformdirs omits appauthor from the path on non-Windows platforms;
    # insert it so all platforms use <author>/<appname>.
    if path.parent.name != APP_AUTHOR:
        path = path.parent / APP_AUTHOR / APP_NAME
    return path

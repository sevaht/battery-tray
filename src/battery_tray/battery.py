"""Reading battery state from the Linux ``/sys/class/power_supply`` tree."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from pathlib import Path

logger = logging.getLogger(__name__)

POWER_SUPPLY_ROOT = Path("/sys/class/power_supply")

# Above this charge, a battery reporting "Not charging" (e.g. a charge-limit
# threshold reached) is treated as on AC rather than discharging.
_NOT_CHARGING_FULL_PERCENT = 75

# Lower bounds (exclusive) for each coarse charge level.
_HIGH_MIN_PERCENT = 90
_GOOD_MIN_PERCENT = 50
_LOW_MIN_PERCENT = 10


class BatteryLevel(StrEnum):
    """Coarse charge level, mapped to a freedesktop icon name for notices."""

    HIGH = "battery-full"
    GOOD = "battery-good"
    LOW = "battery-low"
    CAUTION = "battery-caution"

    @classmethod
    def for_capacity(cls, capacity: int) -> BatteryLevel:
        if capacity > _HIGH_MIN_PERCENT:
            return cls.HIGH
        if capacity > _GOOD_MIN_PERCENT:
            return cls.GOOD
        if capacity > _LOW_MIN_PERCENT:
            return cls.LOW
        return cls.CAUTION


@dataclass(frozen=True, kw_only=True)
class BatteryStatus:
    name: str
    capacity: int
    charging: bool
    status: str
    remaining: timedelta

    @property
    def level(self) -> BatteryLevel:
        return BatteryLevel.for_capacity(self.capacity)


def _clamp_percent(percent: int) -> int:
    return max(0, min(percent, 100))


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _read_int(path: Path) -> int | None:
    text = _read_text(path)
    if text is None:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def list_batteries(root: Path = POWER_SUPPLY_ROOT) -> list[str]:
    """Return the names of power supplies of type ``Battery``, sorted."""
    if not root.is_dir():
        return []
    return [
        entry.name
        for entry in sorted(root.iterdir())
        if _read_text(entry / "type") == "Battery"
    ]


def _time_remaining(base: Path) -> timedelta:
    # Prefer energy/power (µWh / µW); fall back to charge/current (µAh / µA).
    for amount_name, rate_name in (
        ("energy_now", "power_now"),
        ("charge_now", "current_now"),
    ):
        amount = _read_int(base / amount_name)
        rate = _read_int(base / rate_name)
        if amount is not None and rate:
            return timedelta(hours=amount / rate)
    return timedelta(0)


def read_battery(
    name: str, *, root: Path = POWER_SUPPLY_ROOT
) -> BatteryStatus | None:
    """Read the current status of battery ``name``, or None if unavailable."""
    base = root / name
    capacity = _read_int(base / "capacity")
    if capacity is None:
        return None
    capacity = _clamp_percent(capacity)
    status = _read_text(base / "status") or "Unknown"
    charging = status in {"Charging", "Full"} or (
        status == "Not charging" and capacity > _NOT_CHARGING_FULL_PERCENT
    )
    # Truncate to whole minutes: it is the granularity we display and makes
    # change-detection stable across polls.
    remaining = timedelta(minutes=_time_remaining(base).total_seconds() // 60)
    return BatteryStatus(
        name=name,
        capacity=capacity,
        charging=charging,
        status=status,
        remaining=remaining,
    )


def status_lines(status: BatteryStatus) -> list[str]:
    """Human-readable status lines (tooltip / notification body)."""
    lines = [
        f"Charge: {status.capacity}%",
        f"Power: {'' if status.charging else 'dis'}connected",
    ]
    total_minutes = int(status.remaining.total_seconds() // 60)
    if total_minutes:
        hours, minutes = divmod(total_minutes, 60)
        lines.append(f"Life: {f'{hours}h ' if hours else ''}{minutes}m")
    return lines

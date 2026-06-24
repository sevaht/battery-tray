from __future__ import annotations

from typing import TYPE_CHECKING

from battery_tray.battery import (
    BatteryLevel,
    list_batteries,
    read_battery,
    status_lines,
)

if TYPE_CHECKING:
    from pathlib import Path


def _make_supply(root: Path, name: str, **files: str) -> None:
    supply = root / name
    supply.mkdir(parents=True)
    for key, value in files.items():
        (supply / key).write_text(value, encoding="utf-8")


def test_list_batteries_filters_non_batteries(tmp_path: Path) -> None:
    _make_supply(tmp_path, "AC", type="Mains")
    _make_supply(tmp_path, "BAT1", type="Battery", capacity="50")
    _make_supply(tmp_path, "BAT0", type="Battery", capacity="80")
    assert list_batteries(tmp_path) == ["BAT0", "BAT1"]


def test_list_batteries_missing_root(tmp_path: Path) -> None:
    assert list_batteries(tmp_path / "nope") == []


def test_read_battery_discharging_with_remaining(tmp_path: Path) -> None:
    _make_supply(
        tmp_path,
        "BAT0",
        type="Battery",
        capacity="80",
        status="Discharging",
        energy_now="50000000",
        power_now="10000000",  # 5 hours remaining
    )
    status = read_battery("BAT0", root=tmp_path)
    assert status is not None
    assert status.capacity == 80
    assert status.charging is False
    assert status.remaining.total_seconds() == 5 * 3600
    assert status.level is BatteryLevel.GOOD


def test_read_battery_charging(tmp_path: Path) -> None:
    _make_supply(
        tmp_path, "BAT0", type="Battery", capacity="95", status="Charging"
    )
    status = read_battery("BAT0", root=tmp_path)
    assert status is not None
    assert status.charging is True
    assert status.level is BatteryLevel.HIGH


def test_read_battery_missing(tmp_path: Path) -> None:
    assert read_battery("BAT9", root=tmp_path) is None


def test_status_lines(tmp_path: Path) -> None:
    _make_supply(
        tmp_path,
        "BAT0",
        type="Battery",
        capacity="42",
        status="Discharging",
        charge_now="4200000",
        current_now="2100000",  # 2 hours
    )
    status = read_battery("BAT0", root=tmp_path)
    assert status is not None
    lines = status_lines(status)
    assert lines[0] == "Charge: 42%"
    assert "disconnected" in lines[1]
    assert lines[2] == "Life: 2h 0m"

"""Command-line entry point for battery-tray."""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

from sevaht_utility.log_utility import add_log_arguments, configure_logging

from . import CONFIG_FILE_NAME, user_config_path
from .battery import list_batteries, read_battery
from .config import (
    MAX_POLL_SECONDS,
    MIN_POLL_SECONDS,
    load_config,
    save_config,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="battery-tray",
        description="Monitor battery status from the system tray.",
    )

    config_group = parser.add_argument_group(
        "config mode",
        "Update saved settings and exit."
        " Cannot be combined with run mode arguments.",
    )
    config_group.add_argument(
        "--list-batteries",
        action="store_true",
        help="List available batteries and exit.",
    )
    config_group.add_argument(
        "--battery",
        metavar="NAME",
        help="Save the battery to monitor by name and exit.",
    )
    config_group.add_argument(
        "--select-battery",
        action="store_true",
        help="Interactively choose a battery to monitor, save it, and exit.",
    )
    config_group.add_argument(
        "--set-poll-seconds",
        type=float,
        metavar="SECONDS",
        help="Save the refresh interval"
        f" ({MIN_POLL_SECONDS:g}-{MAX_POLL_SECONDS:g}s) and exit.",
    )

    run_group = parser.add_argument_group(
        "run mode",
        "Start the tray. Cannot be combined with config mode arguments.",
    )
    run_group.add_argument(
        "--show",
        action="store_true",
        help="Show the window at startup instead of starting tray-only.",
    )

    add_log_arguments(parser)
    return parser


def _battery_label(name: str) -> str:
    status = read_battery(name)
    if status is None:
        return f"{name} (unavailable)"
    state = "charging" if status.charging else "discharging"
    return f"{name} - {status.capacity}% ({state})"


def _print_batteries() -> int:
    batteries = list_batteries()
    if not batteries:
        print("No batteries detected.")
        return 0
    for name in batteries:
        print(_battery_label(name))
    return 0


def _save_battery(name: str, config_path: Path) -> int:
    config = load_config(config_path)
    config.battery = name
    save_config(config_path, config)
    note = "" if name in list_batteries() else " (not currently detected)"
    print(f"Battery set to {name}{note}.")
    return 0


def _select_and_save_battery(config_path: Path) -> int:
    batteries = list_batteries()
    if not batteries:
        print("No batteries detected.")
        return 1
    print("Available batteries:")
    for menu_number, name in enumerate(batteries, start=1):
        print(f"  {menu_number}) {_battery_label(name)}")
    while True:
        try:
            choice = input("Select battery number (blank to cancel): ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            return 1
        if choice == "":
            print("No battery selected.")
            return 1
        if choice.isdigit() and 1 <= int(choice) <= len(batteries):
            return _save_battery(batteries[int(choice) - 1], config_path)
        print("Invalid selection.")


def _save_poll_seconds(
    seconds: float, parser: argparse.ArgumentParser, config_path: Path
) -> int:
    if not (MIN_POLL_SECONDS <= seconds <= MAX_POLL_SECONDS):
        parser.error(
            "--set-poll-seconds must be between"
            f" {MIN_POLL_SECONDS:g} and {MAX_POLL_SECONDS:g}"
        )
    config = load_config(config_path)
    config.poll_seconds = seconds
    save_config(config_path, config)
    print(f"Refresh interval set to {seconds:g}s.")
    return 0


def _validate_mode_combination(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> None:
    config_flags = [
        label
        for active, label in (
            (args.list_batteries, "--list-batteries"),
            (args.battery is not None, "--battery"),
            (args.select_battery, "--select-battery"),
            (args.set_poll_seconds is not None, "--set-poll-seconds"),
        )
        if active
    ]
    if len(config_flags) > 1:
        parser.error(
            f"these arguments cannot be combined: {', '.join(config_flags)}"
        )
    if config_flags and args.show:
        parser.error(
            f"config argument {config_flags[0]} cannot be combined with --show"
        )


def _run_config_mode(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
    config_path: Path,
) -> int | None:
    """Handle a config-mode argument, or return None if none is active."""
    if args.list_batteries:
        return _print_batteries()
    if args.select_battery:
        return _select_and_save_battery(config_path)
    if args.battery is not None:
        return _save_battery(args.battery, config_path)
    if args.set_poll_seconds is not None:
        return _save_poll_seconds(args.set_poll_seconds, parser, config_path)
    return None


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    configure_logging(args)

    config_path = user_config_path() / CONFIG_FILE_NAME
    _validate_mode_combination(args, parser)

    config_result = _run_config_mode(args, parser, config_path)
    if config_result is not None:
        return config_result

    # Imported lazily so config mode does not require a display / sevaht-gui.
    from .app import BatteryTray

    return BatteryTray(config_path=config_path).run(start_hidden=not args.show)

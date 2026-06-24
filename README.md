# battery-tray

A small Linux system-tray battery monitor, built on
[sevaht-gui](https://github.com/sevaht/sevaht-gui).

- A tray icon shows the selected battery's charge as a colour-graded battery
  glyph (green → red) with charge/charging state in the tooltip.
- Left-click (or the tray menu's **Configure…**) opens a window to pick which
  battery to monitor and set the refresh interval; both are saved under
  `sevaht/battery-tray`.
- Desktop notifications (via `notify-send`) fire when the charge level or
  charging state changes.
- If no system tray is available, the window simply runs on its own.

## Running

```console
$ battery-tray            # start in the tray (window hidden)
$ battery-tray --show     # start with the window open
```

## Configuring from the CLI

These update the saved config and exit (handy for scripts/keybinds); the
running app picks the same values up from config:

```console
$ battery-tray --list-batteries       # show detected batteries and exit
$ battery-tray --battery BAT0         # set the monitored battery by name
$ battery-tray --select-battery       # choose interactively from a list
$ battery-tray --set-poll-seconds 10  # set the refresh interval (1-3600s)
```

Reads battery state from `/sys/class/power_supply` (Linux only).

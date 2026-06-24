"""Draws the battery tray/window icon with PIL.

The icon is a battery outline (optionally with a nub) filled from the bottom in
proportion to the charge, colored on a green-to-red gradient. It renders at any
requested square size so the tray host can scale it cleanly.
"""

from __future__ import annotations

import colorsys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw

if TYPE_CHECKING:
    from collections.abc import Callable

_FULL_PERCENT = 100


def _clamp_percent(percent: int) -> int:
    return max(0, min(percent, _FULL_PERCENT))


def power_gradient_color(percent: int) -> tuple[int, int, int]:
    """Green (100%) to red (0%) through yellow/orange, as an RGB tuple."""
    percent = _clamp_percent(percent)
    # Hue 120deg (green) at full, 0deg (red) at empty.
    hue = (percent / _FULL_PERCENT) * 120 / 360
    red, green, blue = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    return (int(red * 255), int(green * 255), int(blue * 255))


@dataclass(kw_only=True)
class IconStyle:
    show_nub: bool = True
    rounded: bool = True
    connected_border_color: str = "rgb(211,215,207)"
    disconnected_border_color: str = "rgb(255,255,0)"
    gap_units: int = 1


@dataclass(kw_only=True)
class _Rectangle:
    left: int = 0
    top: int = 0
    right: int = 0
    bottom: int = 0

    @property
    def components(self) -> list[int]:
        return [self.left, self.top, self.right - 1, self.bottom - 1]

    @property
    def height(self) -> int:
        return abs(self.bottom - self.top)

    def offset(self, *, top: int = 0) -> _Rectangle:
        return _Rectangle(
            left=self.left,
            top=self.top + top,
            right=self.right,
            bottom=self.bottom,
        )

    def offset_edges(self, amount: int) -> _Rectangle:
        return _Rectangle(
            left=self.left + amount,
            top=self.top + amount,
            right=self.right - amount,
            bottom=self.bottom - amount,
        )

    def draw(
        self,
        draw: ImageDraw.ImageDraw,
        *,
        radius: int = 0,
        width: int = 1,
        fill: str | tuple[int, int, int] | None = None,
        outline: str | tuple[int, int, int] | None = None,
    ) -> None:
        # Skip empty or inverted rectangles (can occur at degenerate sizes).
        if self.right <= self.left or self.bottom <= self.top:
            return
        if radius:
            draw.rounded_rectangle(
                self.components,
                radius=radius,
                fill=fill,
                outline=outline,
                width=width,
            )
        else:
            draw.rectangle(
                self.components, fill=fill, outline=outline, width=width
            )


def render_battery(
    size: int, percent: int, *, connected: bool, style: IconStyle
) -> Image.Image:
    """Render the battery icon at ``size`` x ``size`` pixels."""
    size = max(1, size)
    percent = _clamp_percent(percent)
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    unit = max(1, size // 16)
    border_width = unit * 2
    body_width = (size * 3) // 4
    padding = (size - body_width) // 2
    border_color = (
        style.connected_border_color
        if connected
        else style.disconnected_border_color
    )

    border = _Rectangle(
        left=padding, right=padding + body_width, top=0, bottom=size
    )
    if style.show_nub:
        nub_width = border_width * 2
        nub_padding = (size - nub_width) // 2
        nub = _Rectangle(
            left=nub_padding,
            right=nub_padding + nub_width,
            top=0,
            bottom=border_width
            * 3
            // 2,  # overlaps the body border on purpose
        )
        nub.draw(
            draw,
            fill=border_color,
            radius=border_width // 2 if style.rounded else 0,
        )
        border = border.offset(top=border_width)

    border.draw(
        draw,
        outline=border_color,
        width=border_width,
        radius=border_width * 3 // 2 if style.rounded else 0,
    )

    inner = border.offset_edges(border_width + style.gap_units * unit)
    inner.top += inner.height * (_FULL_PERCENT - percent) // _FULL_PERCENT
    inner.draw(draw, fill=power_gradient_color(percent))
    return image


def battery_renderer(
    percent: int, *, connected: bool, style: IconStyle
) -> Callable[[int], Image.Image]:
    """Return an icon renderer (``size -> image``) for a fixed battery state."""

    def render(size: int) -> Image.Image:
        return render_battery(size, percent, connected=connected, style=style)

    return render

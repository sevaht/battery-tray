from battery_tray.render import IconStyle, power_gradient_color, render_battery


def test_gradient_endpoints() -> None:
    assert power_gradient_color(100) == (0, 255, 0)  # full -> green
    assert power_gradient_color(0) == (255, 0, 0)  # empty -> red


def test_gradient_clamps_out_of_range() -> None:
    assert power_gradient_color(150) == power_gradient_color(100)
    assert power_gradient_color(-10) == power_gradient_color(0)


def test_render_battery_size_and_mode() -> None:
    image = render_battery(48, 50, connected=True, style=IconStyle())
    assert image.size == (48, 48)
    assert image.mode == "RGBA"


def test_render_battery_tiny_size_does_not_crash() -> None:
    image = render_battery(1, 0, connected=False, style=IconStyle())
    assert image.size == (1, 1)

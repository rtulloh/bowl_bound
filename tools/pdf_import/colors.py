"""Convert supported PDF RGB, grayscale and DeviceCMYK values to byte RGB evidence."""

from math import isfinite


class PDFColorError(ValueError):
    """A PDF fill uses an unsupported color shape or value."""


def pdf_color_shape_matches(value: object, color_space: str | None) -> bool:
    """Check reported components against an explicit PDF device color space."""
    if color_space is None:
        return True
    if color_space == "DeviceGray":
        return type(value) in (int, float) or isinstance(value, (tuple, list)) and len(value) == 1
    expected = {"DeviceRGB": 3, "DeviceCMYK": 4}.get(color_space)
    return expected is not None and isinstance(value, (tuple, list)) and len(value) == expected


def rgb_from_pdf_color(value: object) -> tuple[int, int, int]:
    """Convert supported DeviceRGB, DeviceGray or DeviceCMYK components to byte RGB."""
    if type(value) in (int, float):
        channels = (value, value, value)
    elif isinstance(value, (tuple, list)) and len(value) == 1:
        channels = (value[0],) * 3
    elif isinstance(value, (tuple, list)) and len(value) == 3:
        channels = tuple(value)
    elif isinstance(value, (tuple, list)) and len(value) == 4:
        components = tuple(value)
        if any(
            type(channel) not in (int, float) or not isfinite(channel) or not 0 <= channel <= 1
            for channel in components
        ):
            raise PDFColorError("unsupported color values")
        cyan, magenta, yellow, black = components
        channels = tuple((1 - ink) * (1 - black) for ink in (cyan, magenta, yellow))
    else:
        raise PDFColorError("unsupported color space")
    if any(type(channel) not in (int, float) or not isfinite(channel) for channel in channels):
        raise PDFColorError("unsupported color values")
    if not all(0 <= channel <= 1 for channel in channels):
        raise PDFColorError("unsupported color values")
    return tuple(round(channel * 255) for channel in channels)

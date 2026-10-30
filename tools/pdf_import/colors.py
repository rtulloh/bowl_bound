"""Convert pdfplumber RGB and grayscale color values to byte RGB evidence."""

from math import isfinite


class PDFColorError(ValueError):
    """A PDF fill uses an unsupported color shape or value."""


def rgb_from_pdf_color(value: object) -> tuple[int, int, int]:
    """Normalize supported DeviceRGB and DeviceGray values to three byte channels."""
    if type(value) in (int, float):
        channels = (value, value, value)
    elif isinstance(value, (tuple, list)) and len(value) == 1:
        channels = (value[0],) * 3
    elif isinstance(value, (tuple, list)) and len(value) == 3:
        channels = tuple(value)
    else:
        raise PDFColorError("unsupported color space")
    if any(type(channel) not in (int, float) or not isfinite(channel) for channel in channels):
        raise PDFColorError("unsupported color values")
    if not all(0 <= channel <= 1 for channel in channels):
        raise PDFColorError("unsupported color values")
    return tuple(round(channel * 255) for channel in channels)

from PIL import Image

from .base import ImageFormat
from .pillow_formats import ALL_FORMATS


# Keeps the list of formats the app can use, and finds formats by name or extension.
class FormatRegistry:
    # Start with an empty list of formats.
    def __init__(self):
        self._formats: list[ImageFormat] = []

    # Register one more format.
    def add(self, fmt: ImageFormat) -> None:
        self._formats.append(fmt)

    # Return a copy of the list, so callers cannot change the registry by accident.
    def all(self) -> list[ImageFormat]:
        return list(self._formats)

    # Find the format that handles a given extension, or None if there is none.
    def by_extension(self, ext: str) -> ImageFormat | None:
        ext = ext.lower()
        return next((f for f in self._formats if ext in f.extensions), None)

    # Return every extension supported by the registered formats, e.g. {"jpg", "png"}.
    def extensions(self) -> set[str]:
        return {e for f in self._formats for e in f.extensions}


# Checks whether Pillow can both read and write a given format on this system.
def _pillow_supports(pil_format: str) -> bool:
    Image.init()  # load the plugins (AVIF, etc.) before checking
    return pil_format in Image.OPEN and pil_format in Image.SAVE


# Creates the registry with only the formats that are actually available.
def build_default_registry() -> FormatRegistry:
    registry = FormatRegistry()
    for fmt in ALL_FORMATS:
        # Skip formats whose codec is missing, so the GUI never shows them.
        if _pillow_supports(fmt.pil_format):
            registry.add(fmt)
    return registry


# Shared registry used by the whole app.
# To add a new format: create its class and add it to ALL_FORMATS.
REGISTRY = build_default_registry()

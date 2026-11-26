from abc import ABC, abstractmethod
from dataclasses import dataclass

from PIL import Image


# Describes what a format can do. Used to decide how to prepare the pixels.
@dataclass(frozen=True)
class FormatCapabilities:
    supports_alpha: bool = False  # True if the format can store transparency


# Base contract for every image format. Each new format must implement it.
class ImageFormat(ABC):
    id: str                               # short name shown on the button, e.g. "jpeg"
    extensions: tuple[str, ...]           # file extensions, e.g. ("jpg", "jpeg")
    capabilities: FormatCapabilities      # what the format supports

    # Reads an image file and returns it as a Pillow image.
    @abstractmethod
    def decode(self, path: str) -> Image.Image:
        """Read the file. Raises an exception if it fails."""

    # Writes a Pillow image to a file in this format.
    @abstractmethod
    def encode(self, image: Image.Image, path: str) -> None:
        """Write the file. Raises an exception if it fails."""

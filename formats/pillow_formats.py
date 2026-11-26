from PIL import Image

from .base import FormatCapabilities, ImageFormat

# Importing pillow_jxl registers the JPEG XL plugin in Pillow.
# If it is not installed, JXL is simply not available.
try:
    import pillow_jxl  # noqa: F401
except ImportError:
    pass


# Generic format that uses Pillow to read and write the image.
class PillowFormat(ImageFormat):
    # Store the format settings for this instance.
    def __init__(self, fmt_id: str, extensions: tuple[str, ...],
                 pil_format: str, supports_alpha: bool):
        self.id = fmt_id                  # name used in the GUI, e.g. "webp"
        self.extensions = extensions      # file extensions handled by this format
        self.pil_format = pil_format      # Pillow format name, e.g. "WEBP"
        self.capabilities = FormatCapabilities(supports_alpha=supports_alpha)

    # Reads the file and returns a copy that stays valid after the file is closed.
    def decode(self, path: str) -> Image.Image:
        with Image.open(path) as im:
            im.load()        # read all pixel data now
            return im.copy() # copy so the image outlives the file handle

    # Writes the image to disk in this format.
    def encode(self, image: Image.Image, path: str) -> None:
        # Only the pixels are passed to save, so no metadata is written.
        image.save(path, format=self.pil_format)


# All formats the app knows about. Registry checks which ones are available.
ALL_FORMATS = [
    PillowFormat("jpeg", ("jpg", "jpeg"), "JPEG", supports_alpha=False),
    PillowFormat("png", ("png",), "PNG", supports_alpha=True),
    PillowFormat("webp", ("webp",), "WEBP", supports_alpha=True),
    PillowFormat("avif", ("avif",), "AVIF", supports_alpha=True),
    PillowFormat("jxl", ("jxl",), "JXL", supports_alpha=True),
]

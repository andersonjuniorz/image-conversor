from io import BytesIO

from PIL import Image, ImageCms, ImageOps


# Puts a transparent image on a white background, removing the alpha channel.
def _flatten_on_white(img: Image.Image) -> Image.Image:
    # Create a plain white RGB canvas of the same size.
    bg = Image.new("RGB", img.size, (255, 255, 255))
    # Paste the image on top, using its alpha channel as the mask.
    bg.paste(img, mask=img.getchannel("A"))
    return bg


# Makes the image mode match the target: RGBA when alpha is kept, RGB otherwise.
def _normalize(img: Image.Image, keep_alpha: bool) -> Image.Image:
    # Check whether the image has transparency, either in its mode or in its info.
    has_alpha = img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info
    # Convert to RGBA if the image has transparency but is in another mode.
    if has_alpha and img.mode != "RGBA":
        img = img.convert("RGBA")
    # Convert to RGB if the image has no transparency and is in another mode.
    elif not has_alpha and img.mode != "RGB":
        img = img.convert("RGB")

    # The target does not support alpha, so flatten the transparency to white.
    if img.mode == "RGBA" and not keep_alpha:
        img = _flatten_on_white(img)
    return img


# Converts the pixels from the image's color profile to sRGB.
def _apply_srgb(img: Image.Image, icc: bytes | None) -> Image.Image:
    """Convert the pixels to sRGB, keeping the colors looking the same."""
    # No color profile means the image is already treated as sRGB.
    if not icc:
        return img
    # Save the alpha channel separately, since the color conversion uses RGB only.
    alpha = img.getchannel("A") if img.mode == "RGBA" else None
    rgb = img.convert("RGB")
    try:
        # Load the source profile and create the sRGB target profile.
        src = ImageCms.ImageCmsProfile(BytesIO(icc))
        dst = ImageCms.createProfile("sRGB")
        # Convert the colors from the source profile to sRGB.
        out = ImageCms.profileToProfile(rgb, src, dst, outputMode="RGB")
    except (ImageCms.PyCMSError, OSError, ValueError):
        # If the profile is invalid, keep the original image.
        return img
    # Put the transparency back on the converted image.
    if alpha is not None:
        out.putalpha(alpha)
    return out


# Full preparation pipeline, applied to every image before it is saved.
def prepare_image(img: Image.Image, keep_alpha: bool) -> Image.Image:
    # Read the color profile before any change, because later steps drop it.
    icc = img.info.get("icc_profile")
    # Rotate the pixels according to the EXIF orientation tag.
    img = ImageOps.exif_transpose(img)
    # Adjust the mode for transparency and flatten when needed.
    img = _normalize(img, keep_alpha)
    # Convert the colors to sRGB.
    return _apply_srgb(img, icc)

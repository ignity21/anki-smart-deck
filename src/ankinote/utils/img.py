import io

from PIL import Image


def resize_to_square(image_bytes: bytes, target_size: int) -> bytes:
    """Resize an image to a square of the given dimensions.

    If the image is already the target size, it is returned unchanged.
    Uses LANCZOS resampling for high-quality downscaling.

    Args:
        image_bytes: Raw image file bytes (any format PIL supports).
        target_size: Width and height in pixels for the output square.

    Returns:
        Image bytes in the original format, resized to target_size x target_size.
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        original_format = img.format
        if img.size != (target_size, target_size):
            img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            img.save(output, format=original_format)
            return output.getvalue()
    return image_bytes


__all__ = [
    "resize_to_square",
]

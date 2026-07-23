import io

from PIL import Image


def resize_to_max_edge(image_bytes: bytes, max_edge: int) -> bytes:
    """Resize an image so its longest edge is at most ``max_edge``.

    The aspect ratio is preserved. Images already within the limit are returned
    unchanged.
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        original_format = img.format
        width, height = img.size
        longest_edge = max(width, height)
        if longest_edge <= max_edge:
            return image_bytes

        scale = max_edge / longest_edge
        new_size = (
            max(1, round(width * scale)),
            max(1, round(height * scale)),
        )
        resized = img.resize(new_size, Image.Resampling.LANCZOS)
        output = io.BytesIO()
        resized.save(output, format=original_format)
        return output.getvalue()


__all__ = [
    "resize_to_max_edge",
]

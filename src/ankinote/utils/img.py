import io

from PIL import Image


def scale(image_bytes: bytes, target_size: int) -> bytes:
    with Image.open(io.BytesIO(image_bytes)) as img:
        original_format = img.format
        if img.size != (target_size, target_size):
            img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            img.save(output, format=original_format)
            return output.getvalue()
    return image_bytes

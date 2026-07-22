"""Tests for image resizing utilities."""

import io

from PIL import Image

from ankinote.utils.img import resize_to_square


def _png_bytes(size: tuple[int, int], color=(123, 45, 67)) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestResizeToSquare:
    def test_resizes_non_square_to_target(self):
        raw = _png_bytes((80, 40))
        result = resize_to_square(raw, 32)
        with Image.open(io.BytesIO(result)) as out:
            assert out.size == (32, 32)

    def test_passthrough_when_already_target_size(self):
        """No resize/copy when the image already matches the target size."""
        raw = _png_bytes((32, 32))
        result = resize_to_square(raw, 32)
        assert result == raw

    def test_preserves_png_format(self):
        raw = _png_bytes((48, 48))
        result = resize_to_square(raw, 24)
        with Image.open(io.BytesIO(result)) as out:
            assert out.format == "PNG"
            assert out.size == (24, 24)

    def test_preserves_jpeg_format(self):
        img = Image.new("RGB", (48, 48), color=(10, 20, 30))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        raw = buf.getvalue()

        result = resize_to_square(raw, 24)
        with Image.open(io.BytesIO(result)) as out:
            assert out.format == "JPEG"
            assert out.size == (24, 24)

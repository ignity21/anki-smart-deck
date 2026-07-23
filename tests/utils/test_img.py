"""Tests for image resizing utilities."""

import io

from PIL import Image

from ankinote.utils.img import resize_to_max_edge


def _png_bytes(size: tuple[int, int], color=(123, 45, 67)) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestResizeToMaxEdge:
    def test_resizes_long_edge_and_preserves_aspect_ratio(self):
        raw = _png_bytes((80, 40))
        result = resize_to_max_edge(raw, 32)
        with Image.open(io.BytesIO(result)) as out:
            assert out.size == (32, 16)

    def test_passthrough_when_image_is_within_limit(self):
        raw = _png_bytes((32, 20))
        result = resize_to_max_edge(raw, 32)
        assert result == raw

    def test_preserves_png_format(self):
        raw = _png_bytes((48, 24))
        result = resize_to_max_edge(raw, 24)
        with Image.open(io.BytesIO(result)) as out:
            assert out.format == "PNG"
            assert out.size == (24, 12)

    def test_preserves_jpeg_format(self):
        img = Image.new("RGB", (24, 48), color=(10, 20, 30))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        raw = buf.getvalue()

        result = resize_to_max_edge(raw, 24)
        with Image.open(io.BytesIO(result)) as out:
            assert out.format == "JPEG"
            assert out.size == (12, 24)

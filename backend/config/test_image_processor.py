"""Tests for the image processor."""

from io import BytesIO
from unittest import TestCase
from unittest.mock import Mock

from PIL import Image

from .image_processor import process_image


class ProcessImageTests(TestCase):
    """Tests for the process_image function."""

    def create_test_image(self, width: int, height: int, format: str = "JPEG") -> BytesIO:
        """Create a test image in memory."""
        image = Image.new("RGB", (width, height), color="red")
        buffer = BytesIO()
        image.save(buffer, format=format)
        buffer.seek(0)
        return buffer

    def create_mock_image_field(self, width: int, height: int, format: str = "JPEG"):
        """Create a mock ImageFieldFile."""
        buffer = self.create_test_image(width, height, format)
        mock_field = Mock()
        mock_field.open = Mock(return_value=buffer)
        mock_field.file = buffer
        mock_field.read = buffer.read
        mock_field.seek = buffer.seek
        return mock_field

    def test_converts_to_webp(self):
        """Image should be converted to WebP format."""
        image_field = self.create_mock_image_field(800, 600)
        result = process_image(image_field, max_width=1000)

        # Verify it's a valid WebP image
        img = Image.open(BytesIO(result.read()))
        self.assertEqual(img.format, "WEBP")

    def test_respects_max_width(self):
        """Image wider than max_width should be resized."""
        image_field = self.create_mock_image_field(2000, 1500)
        result = process_image(image_field, max_width=1000)

        img = Image.open(BytesIO(result.read()))
        self.assertEqual(img.width, 1000)
        # Aspect ratio should be preserved
        self.assertEqual(img.height, 750)

    def test_does_not_upscale(self):
        """Image smaller than max_width should not be upscaled."""
        image_field = self.create_mock_image_field(500, 400)
        result = process_image(image_field, max_width=1000)

        img = Image.open(BytesIO(result.read()))
        self.assertEqual(img.width, 500)
        self.assertEqual(img.height, 400)

    def test_crop_to_square(self):
        """Image should be cropped to square when crop=True with 1:1 ratio."""
        # Wide image
        image_field = self.create_mock_image_field(1000, 500)
        result = process_image(image_field, max_width=2000, crop=True, crop_ratio=(1, 1))

        img = Image.open(BytesIO(result.read()))
        # Should be cropped to square (width == height)
        self.assertEqual(img.width, img.height)
        self.assertEqual(img.width, 500)

    def test_crop_tall_image(self):
        """Tall image should be cropped correctly."""
        # Tall image
        image_field = self.create_mock_image_field(500, 1000)
        result = process_image(image_field, max_width=2000, crop=True, crop_ratio=(1, 1))

        img = Image.open(BytesIO(result.read()))
        # Should be cropped to square
        self.assertEqual(img.width, img.height)
        self.assertEqual(img.width, 500)

    def test_no_crop_when_disabled(self):
        """Image should maintain aspect ratio when crop=False."""
        image_field = self.create_mock_image_field(1000, 500)
        result = process_image(image_field, max_width=2000, crop=False)

        img = Image.open(BytesIO(result.read()))
        self.assertEqual(img.width, 1000)
        self.assertEqual(img.height, 500)

    def test_custom_crop_ratio(self):
        """Should crop to custom aspect ratio."""
        # Square image cropped to 16:9
        image_field = self.create_mock_image_field(1000, 1000)
        result = process_image(image_field, max_width=2000, crop=True, crop_ratio=(16, 9))

        img = Image.open(BytesIO(result.read()))
        # Should be 16:9 ratio
        ratio = img.width / img.height
        self.assertAlmostEqual(ratio, 16 / 9, places=2)

    def test_quality_parameter(self):
        """Quality parameter should be accepted and used."""
        image_field = self.create_mock_image_field(800, 600)
        result = process_image(image_field, max_width=2000, quality=50)

        # Verify it produces valid webp output
        img = Image.open(BytesIO(result.read()))
        self.assertEqual(img.format, "WEBP")
        self.assertEqual(img.width, 800)
        self.assertEqual(img.height, 600)

    def test_converts_rgb(self):
        """Image should be converted to RGB mode."""
        # Create RGBA image
        image = Image.new("RGBA", (100, 100), color="red")
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)

        image_field = self.create_mock_image_field(100, 100)
        image_field.file = buffer

        result = process_image(image_field, max_width=1000)
        img = Image.open(BytesIO(result.read()))

        # Should be RGB, not RGBA
        self.assertEqual(img.mode, "RGB")

    def test_upscales_with_min_width(self):
        """Image smaller than min_width should be upscaled."""
        image_field = self.create_mock_image_field(500, 400)
        result = process_image(image_field, max_width=2000, min_width=1000)

        img = Image.open(BytesIO(result.read()))
        self.assertEqual(img.width, 1000)
        # Aspect ratio should be preserved
        self.assertEqual(img.height, 800)

    def test_min_width_and_max_width_together(self):
        """min_width should be applied before max_width."""
        # Image that needs upscaling but would exceed max_width
        image_field = self.create_mock_image_field(800, 600)
        result = process_image(image_field, max_width=1500, min_width=2000)

        img = Image.open(BytesIO(result.read()))
        # Should be clamped to max_width after upscaling
        self.assertEqual(img.width, 1500)
        self.assertEqual(img.height, 1125)

    def test_no_upscale_without_min_width(self):
        """Without min_width, small images should not be upscaled."""
        image_field = self.create_mock_image_field(500, 400)
        result = process_image(image_field, max_width=2000)

        img = Image.open(BytesIO(result.read()))
        # Should remain original size
        self.assertEqual(img.width, 500)
        self.assertEqual(img.height, 400)

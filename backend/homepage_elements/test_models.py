"""Tests for homepage_elements models."""

from io import BytesIO
from unittest import TestCase

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from .models import HeroImageElement


class HeroImageElementValidationTest(TestCase):
    """Test validation for HeroImageElement minimum dimensions."""

    def create_test_image(self, width: int, height: int) -> SimpleUploadedFile:
        """Create a test image with specific dimensions."""
        img = Image.new("RGB", (width, height), color="red")
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        buffer.seek(0)
        return SimpleUploadedFile("test.jpg", buffer.read(), content_type="image/jpeg")

    def test_image_below_min_width_raises_validation_error(self):
        """Image width below minimum should raise ValidationError."""
        hero = HeroImageElement()
        hero.image = self.create_test_image(1000, 600)

        with self.assertRaises(ValidationError) as cm:
            hero.clean()

        error_message = str(cm.exception)
        self.assertIn("1440x532", error_message)
        self.assertIn("1000x600", error_message)

    def test_image_below_min_height_raises_validation_error(self):
        """Image height below minimum should raise ValidationError."""
        hero = HeroImageElement()
        hero.image = self.create_test_image(1500, 400)

        with self.assertRaises(ValidationError) as cm:
            hero.clean()

        error_message = str(cm.exception)
        self.assertIn("1440x532", error_message)
        self.assertIn("1500x400", error_message)

    def test_image_at_minimum_dimensions_passes_validation(self):
        """Image at exactly minimum dimensions should pass."""
        hero = HeroImageElement()
        hero.image = self.create_test_image(1440, 532)

        # Should not raise
        hero.clean()

    def test_image_above_minimum_dimensions_passes_validation(self):
        """Image larger than minimum should pass."""
        hero = HeroImageElement()
        hero.image = self.create_test_image(1920, 1080)

        # Should not raise
        hero.clean()

    def test_no_image_does_not_raise(self):
        """clean() should not crash when no image is set."""
        hero = HeroImageElement()
        # Should not raise
        hero.clean()

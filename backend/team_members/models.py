from django.core.files.uploadedfile import UploadedFile
from django.db import models

from config.image_processor import process_image


class TeamMember(models.Model):
    name = models.CharField(max_length=255)
    role_de = models.CharField(max_length=255, verbose_name="Role (German)", default="")
    role_en = models.CharField(max_length=255, verbose_name="Role (English)", default="")
    image = models.ImageField(upload_to="team/")
    order = models.IntegerField(default=0, help_text="Display order (lower numbers appear first)")
    last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        # Only process if a new image file is being uploaded
        # Check if image has a file object attached (not just a string path)
        if self.image and hasattr(self.image, "_file") and isinstance(self.image._file, UploadedFile):
            processed = process_image(
                image_field=self.image,
                max_width=800,
                quality=75,
            )
            self.image.save(f"{self.image.name.split('.')[0]}.webp", processed, save=False)
        super().save(*args, **kwargs)

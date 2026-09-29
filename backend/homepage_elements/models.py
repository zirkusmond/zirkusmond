from django.db import models
from tinymce import models as tinymce_models


class HomePageElement(models.Model):
    title_de = models.CharField(max_length=100)
    title_en = models.CharField(max_length=100)
    message_de = tinymce_models.HTMLField(max_length=1000)
    message_en = tinymce_models.HTMLField(max_length=1000)
    active = models.BooleanField(default=False)
    link = models.CharField(max_length=255, blank=True)

    # Declared explicitly so subclasses (and this base class itself, via
    # type(self) in save()) have a statically known manager - Django would
    # otherwise add the same default manager to each concrete subclass anyway.
    objects: models.Manager["HomePageElement"] = models.Manager()

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return self.title_de

    def save(self, *args, **kwargs):
        # Only one element of a given type may be active at a time: activating
        # this one deactivates every other row of the same concrete model.
        if self.active:
            type(self).objects.exclude(pk=self.pk).filter(active=True).update(active=False)
        super().save(*args, **kwargs)


# For now this class system is a bit over the top, because for now they all havethe same fields
# BUt maybe in the future certain elements will need additional fields so then it will make sense
#
class PopUpElement(HomePageElement):
    """A dismissible pop-up shown on the homepage. Rendered bottom-right on
    desktop, bottom-center on mobile — the position is fixed in the frontend."""


class PreShowsElement(HomePageElement):
    """A section content element displayed before the shows element."""


class PostShowsElement(HomePageElement):
    """A section content element displayed after the shows element, before the footer."""


class HeroImageElement(models.Model):
    """Custom hero image for the homepage. When active, replaces the default hero image."""

    image = models.ImageField(upload_to="hero_images/")
    active = models.BooleanField(default=False)

    objects: models.Manager["HeroImageElement"] = models.Manager()

    def __str__(self) -> str:
        return f"Hero Image ({self.image.name})"

    def save(self, *args, **kwargs):
        # Only one hero image may be active at a time
        if self.active:
            type(self).objects.exclude(pk=self.pk).filter(active=True).update(active=False)
        super().save(*args, **kwargs)

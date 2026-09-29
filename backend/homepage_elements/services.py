from .models import HeroImageElement, HomePageElement
from .serializers import homepage_element_serializer


def get_active_homepage_elements() -> list[dict]:
    """Serialized payload for every active concrete HomePageElement.

    Each entry carries a ``type`` discriminator (the model name) so the
    frontend can tell the element kinds apart.
    """
    elements: list[dict] = []
    for subclass in HomePageElement.__subclasses__():
        serializer = homepage_element_serializer(subclass)
        for element in subclass.objects.filter(active=True):
            elements.append({**serializer(element).data, "type": subclass._meta.model_name})

    return elements


def get_active_hero_image() -> dict | None:
    """Returns the active hero image if one exists."""
    hero_image = HeroImageElement.objects.filter(active=True).first()
    if hero_image:
        serializer = homepage_element_serializer(HeroImageElement)
        return serializer(hero_image).data
    return None

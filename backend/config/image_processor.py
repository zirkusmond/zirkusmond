from io import BytesIO

from django.core.files.base import ContentFile
from django.db.models.fields.files import ImageFieldFile
from PIL import Image, ImageOps


def process_image(
    image_field: ImageFieldFile,
    max_width: int,
    quality: int = 65,
    crop: bool = False,
    crop_ratio: tuple[int, int] = (1, 1),
    min_width: int | None = None,
) -> ContentFile:
    """
    Process an image: handle EXIF orientation, optionally crop, resize, and convert to webp.

    Args:
        image_field: Django ImageField file to process
        max_width: Maximum width in pixels
        quality: WebP quality (0-100)
        crop: Whether to crop to target ratio
        crop_ratio: Target aspect ratio as (width, height) tuple
        min_width: Minimum width in pixels (upscales if needed)

    Returns:
        ContentFile with processed webp image
    """
    img: Image.Image = Image.open(image_field)
    img = ImageOps.exif_transpose(img)  # respect camera rotation
    img = img.convert("RGB")

    # crop to target ratio (center crop)
    if crop:
        target_w, target_h = crop_ratio
        current_ratio = img.width / img.height
        target_ratio = target_w / target_h

        if current_ratio > target_ratio:
            new_width = int(img.height * target_ratio)
            left = (img.width - new_width) // 2
            img = img.crop((left, 0, left + new_width, img.height))

        else:
            new_height = int(img.width / target_ratio)
            top = (img.height - new_height) // 2
            img = img.crop((0, top, img.width, top + new_height))

    # Apply min_width first (upscale if needed)
    if min_width and img.width < min_width:
        new_height = int(min_width * img.height / img.width)
        img = img.resize((min_width, new_height), Image.Resampling.LANCZOS)

    # Apply max_width (downscale if needed)
    if img.width > max_width:
        new_height = int(max_width * img.height / img.width)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

    buffer = BytesIO()
    img.save(buffer, format="WEBP", quality=quality, method=6)

    return ContentFile(buffer.getvalue())

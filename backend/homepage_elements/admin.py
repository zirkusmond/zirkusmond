from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import HeroImageElement, PopUpElement, PostShowsElement, PreShowsElement


class PopUpElementAdmin(ModelAdmin):
    list_display = ("title_en", "active", "link")


class PreShowsElementAdmin(ModelAdmin):
    list_display = ("title_en", "active", "link")


class PostShowsElementAdmin(ModelAdmin):
    list_display = ("title_en", "active", "link")


class HeroImageElementAdmin(ModelAdmin):
    list_display = ("__str__", "active")
    readonly_fields = ("image_preview", "mobile_image_preview")

    @admin.display(description="Desktop Preview")
    def image_preview(self, obj):
        if obj.image:
            return f'<img src="{obj.image.url}" style="max-width: 300px; max-height: 200px;" />'
        return "No image"

    @admin.display(description="Mobile Preview")
    def mobile_image_preview(self, obj):
        if obj.mobile_image:
            return (
                f'<img src="{obj.mobile_image.url}" style="max-width: 200px; max-height: 300px;" />'
            )
        return "No mobile image"

    image_preview.allow_tags = True
    mobile_image_preview.allow_tags = True

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["image"].help_text = (
            "Minimum size: 1440x532px. Recommended aspect ratio: 2.7:1 (landscape). "
            "Images will be converted to WebP automatically."
        )
        form.base_fields["mobile_image"].help_text = (
            "Optional mobile-specific image. Recommended: portrait or 1:1 format. "
            "If not provided, the desktop image will be used. Images will be converted to WebP automatically."
        )
        return form


admin.site.register(
    PopUpElement,
    PopUpElementAdmin,
)
admin.site.register(
    PreShowsElement,
    PreShowsElementAdmin,
)
admin.site.register(
    PostShowsElement,
    PostShowsElementAdmin,
)
admin.site.register(
    HeroImageElement,
    HeroImageElementAdmin,
)

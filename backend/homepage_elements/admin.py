from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import PopUpElement, PostShowsElement, PreShowsElement, HeroImageElement


class PopUpElementAdmin(ModelAdmin):
    list_display = ("title_en", "active", "link")


class PreShowsElementAdmin(ModelAdmin):
    list_display = ("title_en", "active", "link")


class PostShowsElementAdmin(ModelAdmin):
    list_display = ("title_en", "active", "link")


class HeroImageElementAdmin(ModelAdmin):
    list_display = ("__str__", "active")
    readonly_fields = ("image_preview",)

    @admin.display(description="Preview")
    def image_preview(self, obj):
        if obj.image:
            return f'<img src="{obj.image.url}" style="max-width: 300px; max-height: 200px;" />'
        return "No image"

    image_preview.allow_tags = True

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["image"].help_text = (
            "Minimum size: 1440x532px. Recommended aspect ratio: 2.7:1 (landscape). "
            "Images will be displayed as-is without cropping or resizing."
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

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
    list_display = ("image", "active")


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

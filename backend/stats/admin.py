from django.contrib import admin
from unfold.admin import ModelAdmin

from . import components  # noqa: F401 -- registers dashboard chart components on import
from .models import PageView


@admin.register(PageView)
class PageViewAdmin(ModelAdmin):
    list_display = ("path", "referer", "device_type", "session_key", "entered_at", "left_at")
    list_filter = ("device_type", "entered_at")
    search_fields = ("path", "session_key")
    readonly_fields = [
        f.name for f in PageView._meta.fields
    ]  # it's log data, don't let admins edit it

    def has_add_permission(self, request):
        return False  # these are created by middleware, not admins

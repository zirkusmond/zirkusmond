from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from . import components  # noqa: F401 -- registers dashboard chart components on import
from .models import PageView

# Django's stock UserAdmin doesn't work with Unfold's templates (no "Add" button),
# so re-register User with Unfold's ModelAdmin.
admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


@admin.register(PageView)
class PageViewAdmin(ModelAdmin):
    list_display = ("path", "device_type", "session_key", "entered_at", "left_at")
    list_filter = ("device_type", "entered_at")
    search_fields = ("path", "session_key")
    readonly_fields = [
        f.name for f in PageView._meta.fields
    ]  # it's log data, don't let admins edit it

    def has_add_permission(self, request):
        return False  # these are created by middleware, not admins

from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import TeamMember


class TeamMemberAdmin(ModelAdmin):
    list_display = ["name", "role_de", "role_en", "order"]
    list_editable = ["order"]
    search_fields = ["name", "role_de", "role_en"]
    ordering = ["order", "name"]


admin.site.register(TeamMember, TeamMemberAdmin)

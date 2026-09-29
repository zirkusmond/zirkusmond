from django.urls import path

from team_members import views

urlpatterns = [
    path("team-members/", views.all_team_members, name="all_team_members"),
]

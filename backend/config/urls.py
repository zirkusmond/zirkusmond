from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

import config.views as views

urlpatterns = [
    # Admin
    path("mondmin/", admin.site.urls),
    path("tinymce/", include("tinymce.urls")),
    # newsletter
    path("newsletter/", include("newsletter.urls")),
    # homepage
    path("", views.homepage),
    # Apps
    path("", include("shows.urls")),
    path("", include("reservations.urls")),
    path("", include("team_members.urls")),
    # Sentry dummy route
    # path("sentry-debug/", views.trigger_error),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path("debug/", include(debug_toolbar.urls)),
    ]

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

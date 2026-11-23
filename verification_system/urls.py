from django.contrib import admin
from django.urls import include, path

from verification import views as verification_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", verification_views.home, name="home"),
    path("accounts/", include("accounts.urls")),
    path("instruments/", include("instruments.urls")),
    path("", include("verification.urls")),
]

# Custom error pages (visible when DEBUG = False)
handler403 = "verification.views.error_403"
handler404 = "verification.views.error_404"
handler500 = "verification.views.error_500"

from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core import views

router = DefaultRouter()
router.register(r"team-group", views.TeamGroupViewSet)
router.register(r"team", views.TeamViewSet)
router.register(r"player", views.PlayerViewSet)
router.register(r"coach", views.CoachViewSet)

urlpatterns = [
    path("admin/", admin.site.urls), 
    path("api/", include(router.urls))
]

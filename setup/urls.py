from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from core import views

router = DefaultRouter()
router.register(r"team-group", views.TeamGroupViewSet)
router.register(r"team", views.TeamViewSet)
router.register(r"player", views.PlayerViewSet)
router.register(r"coach", views.CoachViewSet)
router.register(r"stadium", views.StadiumViewSet)
router.register(r"match", views.MatchViewSet)
router.register(r"goal", views.GoalViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]

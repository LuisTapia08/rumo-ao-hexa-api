from rest_framework import viewsets
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)

from core import models, serializers


class ModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]


class TeamGroupViewSet(ModelViewSet):
    queryset = models.TeamGroup.objects.all()
    serializer_class = serializers.TeamGroupSerializer


class TeamViewSet(ModelViewSet):
    queryset = models.Team.objects.all()
    serializer_class = serializers.TeamSerializer


class PlayerViewSet(ModelViewSet):
    queryset = models.Player.objects.all()
    serializer_class = serializers.PlayerSerializer


class CoachViewSet(ModelViewSet):
    queryset = models.Coach.objects.all()
    serializer_class = serializers.CoachSerializer

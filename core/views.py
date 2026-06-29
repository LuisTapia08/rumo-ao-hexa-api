from rest_framework import viewsets

from core import models, serializers


class TeamGroupViewSet(viewsets.ModelViewSet):
    queryset = models.TeamGroup.objects.all()
    serializer_class = serializers.TeamGroupSerializer


class TeamViewSet(viewsets.ModelViewSet):
    queryset = models.Team.objects.all()
    serializer_class = serializers.TeamSerializer


class PlayerViewSet(viewsets.ModelViewSet):
    queryset = models.Player.objects.all()
    serializer_class = serializers.PlayerSerializer


class CoachViewSet(viewsets.ModelViewSet):
    queryset = models.Coach.objects.all()
    serializer_class = serializers.CoachSerializer

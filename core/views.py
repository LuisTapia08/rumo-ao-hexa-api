from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from core import filters, models, serializers


class BaseViewSet(viewsets.ModelViewSet):
    # Leitura pública; criar/editar/apagar exige token JWT
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]


class TeamGroupViewSet(BaseViewSet):
    queryset = models.TeamGroup.objects.order_by("id")
    filterset_class = filters.TeamGroupFilter
    serializer_class = serializers.TeamGroupSerializer


class TeamViewSet(BaseViewSet):
    queryset = models.Team.objects.select_related("team_group").order_by("id")
    filterset_class = filters.TeamFilter
    serializer_class = serializers.TeamSerializer


class PlayerViewSet(BaseViewSet):
    queryset = models.Player.objects.select_related("team").order_by("id")
    filterset_class = filters.PlayerFilter
    serializer_class = serializers.PlayerSerializer

    @action(detail=False, methods=["get"], url_path="canhotos")
    def canhotos(self, request):
        players = self.filter_queryset(self.get_queryset()).filter(
            foot_preference=models.Player.FootPreference.LEFT
        )
        page = self.paginate_queryset(players)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class CoachViewSet(BaseViewSet):
    queryset = models.Coach.objects.select_related("team").order_by("id")
    filterset_class = filters.CoachFilter
    serializer_class = serializers.CoachSerializer

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from core import filters, models, serializers, services


class BaseViewSet(viewsets.ModelViewSet):
    # Leitura pública; criar/editar/apagar exige token JWT
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]


class TeamGroupViewSet(BaseViewSet):
    queryset = models.TeamGroup.objects.order_by("id")
    filterset_class = filters.TeamGroupFilter
    serializer_class = serializers.TeamGroupSerializer

    @action(detail=True, methods=["get"], url_path="classificacao")
    def classificacao(self, request, pk=None):
        group = self.get_object()
        return Response(services.group_standings(group))


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

    @action(detail=False, methods=["get"], url_path="artilheiros")
    def artilheiros(self, request):
        scorers = services.top_scorers(models.Goal.objects.all())
        team = request.query_params.get("team")
        if team:
            scorers = scorers.filter(team__name__iexact=team)
        page = self.paginate_queryset(scorers)
        serializer = serializers.TopScorerSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class CoachViewSet(BaseViewSet):
    queryset = models.Coach.objects.select_related("team").order_by("id")
    filterset_class = filters.CoachFilter
    serializer_class = serializers.CoachSerializer


class StadiumViewSet(BaseViewSet):
    queryset = models.Stadium.objects.order_by("name", "id")
    filterset_class = filters.StadiumFilter
    serializer_class = serializers.StadiumSerializer


class MatchViewSet(BaseViewSet):
    queryset = (
        models.Match.objects.select_related(
            "home_team", "away_team", "stadium", "team_group"
        )
        .prefetch_related("goals__player__team")
        .order_by("kickoff", "id")
    )
    filterset_class = filters.MatchFilter
    serializer_class = serializers.MatchSerializer


class GoalViewSet(BaseViewSet):
    queryset = models.Goal.objects.select_related(
        "player__team", "match__home_team", "match__away_team"
    ).order_by("match__kickoff", "minute", "stoppage_minute", "id")
    filterset_class = filters.GoalFilter
    serializer_class = serializers.GoalSerializer

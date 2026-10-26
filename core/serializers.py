from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from core import models


class ModelSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = models.ModelBase
        fields = "__all__"


class TeamGroupSerializer(ModelSerializer):
    class Meta:
        model = models.TeamGroup
        fields = "__all__"


class TeamSerializer(ModelSerializer):
    class Meta:
        model = models.Team
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["team_group"] = (
            instance.team_group.name if instance.team_group else "Fora da copa"
        )
        return representation


class PlayerSerializer(ModelSerializer):
    class Meta:
        model = models.Player
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["team"] = instance.team.name
        representation["shirt_size"] = (
            instance.get_shirt_size_display() if instance.shirt_size else None
        )
        representation["position"] = (
            instance.get_position_display() if instance.position else None
        )
        representation["foot_preference"] = (
            instance.get_foot_preference_display() if instance.foot_preference else None
        )
        return representation


class CoachSerializer(ModelSerializer):
    class Meta:
        model = models.Coach
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["shirt_size"] = (
            instance.get_shirt_size_display() if instance.shirt_size else None
        )
        return representation


class StadiumSerializer(ModelSerializer):
    is_active = serializers.BooleanField(required=False)

    class Meta:
        model = models.Stadium
        fields = "__all__"


def _run_model_clean(model_class, serializer, attrs):
    """Monta uma instância não salva (mesclando com a existente, se houver),
    chama clean() e converte ValidationError do Django em erro 400 do DRF."""
    instance = serializer.instance
    data = {}
    if instance is not None:
        for field in model_class._meta.concrete_fields:
            if field.name not in ("id", "created_at", "updated_at"):
                data[field.name] = getattr(instance, field.name)
    data.update(attrs)
    candidate = model_class(**data)
    if instance is not None:
        candidate.pk = instance.pk
    try:
        candidate.clean()
    except DjangoValidationError as exc:
        raise serializers.ValidationError(exc.message_dict)
    return attrs


class GoalNestedSerializer(serializers.ModelSerializer):
    player_name = serializers.CharField(source="player.name", read_only=True)
    scoring_team = serializers.CharField(source="scoring_team.name", read_only=True)

    class Meta:
        model = models.Goal
        fields = [
            "id",
            "player",
            "player_name",
            "minute",
            "stoppage_minute",
            "is_penalty",
            "is_own_goal",
            "scoring_team",
        ]


class MatchSerializer(ModelSerializer):
    is_active = serializers.BooleanField(required=False)
    home_team_name = serializers.CharField(source="home_team.name", read_only=True)
    away_team_name = serializers.CharField(source="away_team.name", read_only=True)
    stadium_name = serializers.CharField(source="stadium.name", read_only=True)
    winner = serializers.SerializerMethodField()
    goals = GoalNestedSerializer(many=True, read_only=True)

    class Meta:
        model = models.Match
        fields = "__all__"

    def get_winner(self, obj):
        winner = obj.winner
        return winner.name if winner else None

    def validate(self, attrs):
        attrs = super().validate(attrs)
        return _run_model_clean(models.Match, self, attrs)


class GoalSerializer(ModelSerializer):
    is_active = serializers.BooleanField(required=False)
    player_name = serializers.CharField(source="player.name", read_only=True)
    scoring_team = serializers.CharField(source="scoring_team.name", read_only=True)

    class Meta:
        model = models.Goal
        fields = "__all__"

    def validate(self, attrs):
        attrs = super().validate(attrs)
        return _run_model_clean(models.Goal, self, attrs)


class TopScorerSerializer(serializers.Serializer):
    player = serializers.CharField(source="name")
    team = serializers.CharField(source="team.name")
    goals = serializers.IntegerField(source="goals_count")
    penalties = serializers.IntegerField(source="penalties_count")

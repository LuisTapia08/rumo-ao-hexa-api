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

from django.contrib import admin

from .models import Coach, Goal, Match, Player, Stadium, Team, TeamGroup

# Register your models here.
admin.site.register(Player)
admin.site.register(Team)
admin.site.register(TeamGroup)
admin.site.register(Coach)
admin.site.register(Stadium)


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_select_related = ("home_team", "away_team")


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_select_related = ("player", "match__home_team", "match__away_team")


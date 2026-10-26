from django.contrib import admin

from .models import Coach, Goal, Match, Player, Stadium, Team, TeamGroup

# Register your models here.
admin.site.register(Player)
admin.site.register(Team)
admin.site.register(TeamGroup)
admin.site.register(Coach)
admin.site.register(Stadium)
admin.site.register(Match)
admin.site.register(Goal)

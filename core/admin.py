from django.contrib import admin

from .models import Coach, Player, Team, TeamGroup

# Register your models here.
admin.site.register(Player)
admin.site.register(Team)
admin.site.register(TeamGroup)
admin.site.register(Coach)

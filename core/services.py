import unicodedata

from django.db.models import Count, Q

from core import models


def _name_key(name):
    # ordem alfabética sem distinguir acentos nem caixa
    decomposed = unicodedata.normalize("NFD", name)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def group_standings(group):
    """Classificação de um grupo: só partidas encerradas da fase de grupos."""
    rows = {
        team.id: {
            "team": team.name,
            "team_id": team.id,
            "points": 0,
            "played": 0,
            "won": 0,
            "drawn": 0,
            "lost": 0,
            "goals_for": 0,
            "goals_against": 0,
            "goal_difference": 0,
        }
        for team in group.teams.all()
    }
    matches = models.Match.objects.filter(
        team_group=group,
        stage=models.Match.Stage.GROUP,
        status=models.Match.Status.FINISHED,
    )
    for match in matches:
        for team_id, scored, conceded in (
            (match.home_team_id, match.home_score, match.away_score),
            (match.away_team_id, match.away_score, match.home_score),
        ):
            row = rows.get(team_id)
            if row is None:
                continue
            row["played"] += 1
            row["goals_for"] += scored
            row["goals_against"] += conceded
            if scored > conceded:
                row["won"] += 1
                row["points"] += 3
            elif scored == conceded:
                row["drawn"] += 1
                row["points"] += 1
            else:
                row["lost"] += 1
    for row in rows.values():
        row["goal_difference"] = row["goals_for"] - row["goals_against"]
    return sorted(
        rows.values(),
        key=lambda r: (-r["points"], -r["goal_difference"], -r["goals_for"], _name_key(r["team"])),
    )


def top_scorers(goals):
    """Jogadores com gols (sem gol contra) dentro do queryset de gols recebido."""
    valid_goals = goals.filter(is_own_goal=False)
    return (
        models.Player.objects.select_related("team")
        .annotate(
            goals_count=Count("goals", filter=Q(goals__in=valid_goals), distinct=True),
            penalties_count=Count(
                "goals",
                filter=Q(goals__in=valid_goals, goals__is_penalty=True),
                distinct=True,
            ),
        )
        .filter(goals_count__gt=0)
        .order_by("-goals_count", "name")
    )

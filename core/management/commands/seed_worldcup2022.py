import json
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from core import models

GROUP_DESCRIPTION = "Fase de grupos da Copa do Mundo FIFA 2022"


def save_validated(model, lookup, values):
    """Cria ou atualiza pela chave natural, validando com full_clean()."""
    instance = model.objects.filter(**lookup).first() or model(**lookup)
    for field, value in values.items():
        setattr(instance, field, value)
    instance.full_clean()
    instance.save()
    return instance


class Command(BaseCommand):
    help = "Carrega os dados da Copa do Mundo 2022 (data/worldcup2022.json)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Apaga gols, partidas, técnicos, jogadores, seleções, estádios e grupos antes de carregar.",
        )

    def handle(self, *args, **options):
        path = settings.BASE_DIR / "data" / "worldcup2022.json"
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        try:
            with transaction.atomic():
                if options["reset"]:
                    self.reset()
                self.load(data)
        except (IntegrityError, ValidationError) as exc:
            raise CommandError(
                f"Falha ao carregar os dados da Copa 2022: {exc}. "
                "Verifique se as migrações foram aplicadas "
                "(`python manage.py migrate`); se o conflito for com dados "
                "locais, rode com --reset."
            ) from exc

        if options["verbosity"] < 1:
            return
        self.stdout.write(
            self.style.SUCCESS(
                "Copa 2022 carregada: "
                f"{models.TeamGroup.objects.count()} grupos, "
                f"{models.Team.objects.count()} seleções, "
                f"{models.Coach.objects.count()} técnicos, "
                f"{models.Player.objects.count()} jogadores, "
                f"{models.Stadium.objects.count()} estádios, "
                f"{models.Match.objects.count()} partidas, "
                f"{models.Goal.objects.count()} gols."
            )
        )

    def reset(self):
        for model in (
            models.Goal,
            models.Match,
            models.Coach,
            models.Player,
            models.Team,
            models.Stadium,
            models.TeamGroup,
        ):
            model.objects.all().delete()

    def load(self, data):
        groups = {}
        team_group_of = {}
        for item in data["groups"]:
            group, _ = models.TeamGroup.objects.update_or_create(
                name=item["name"], defaults={"description": GROUP_DESCRIPTION}
            )
            groups[item["name"]] = group
            for team_name in item["teams"]:
                team_group_of[team_name] = group

        teams = {}
        for item in data["teams"]:
            team, _ = models.Team.objects.update_or_create(
                name=item["name"],
                defaults={
                    "federation": item["federation"],
                    "team_group": team_group_of[item["name"]],
                },
            )
            teams[item["name"]] = team
            models.Coach.objects.update_or_create(name=item["coach"], team=team)

        stadiums = {}
        for item in data["stadiums"]:
            stadium, _ = models.Stadium.objects.update_or_create(
                name=item["name"],
                defaults={"city": item["city"], "capacity": item["capacity"]},
            )
            stadiums[item["name"]] = stadium

        for item in data["matches"]:
            home, away = teams[item["home"]], teams[item["away"]]
            match = save_validated(
                models.Match,
                {"home_team": home, "away_team": away, "stage": item["stage"]},
                {
                    "stadium": stadiums[item["stadium"]],
                    "kickoff": datetime.fromisoformat(item["kickoff"]),
                    "team_group": groups[item["group"]] if item["group"] else None,
                    "status": models.Match.Status.FINISHED,
                    "home_score": item["home_score"],
                    "away_score": item["away_score"],
                    "home_penalties": item["home_penalties"],
                    "away_penalties": item["away_penalties"],
                },
            )
            for goal in item["goals"]:
                player, _ = models.Player.objects.update_or_create(
                    name=goal["player"], team=teams[goal["team"]]
                )
                save_validated(
                    models.Goal,
                    {
                        "match": match,
                        "player": player,
                        "minute": goal["minute"],
                        "stoppage_minute": goal["stoppage_minute"],
                    },
                    {
                        "is_penalty": goal["is_penalty"],
                        "is_own_goal": goal["is_own_goal"],
                    },
                )

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


# Create your models here.
class ModelBase(models.Model):
    id = models.AutoField(primary_key=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Person(ModelBase):
    class ShirtSize(models.TextChoices):
        XS = "XS", "Extra Small"
        S = "S", "Small"
        M = "M", "Medium"
        L = "L", "Large"
        XL = "XL", "Extra Large"

    name = models.CharField(max_length=255)
    birth_date = models.DateField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True)
    weight = models.FloatField(null=True, blank=True)
    foot_size = models.FloatField(null=True, blank=True)
    shirt_size = models.CharField(
        max_length=2, choices=ShirtSize.choices, null=True, blank=True
    )

    def __str__(self):
        return self.name

    class Meta:
        abstract = True


class TeamGroup(ModelBase):
    name = models.CharField(max_length=50)
    description = models.TextField()

    class Meta:
        verbose_name = "Team Group"
        verbose_name_plural = "Team Groups"

    def __str__(self):
        return self.name


class Player(Person):
    class Position(models.TextChoices):
        GOALKEEPER = "GK", "Goalkeeper"
        DEFENDER = "DF", "Defender"
        MIDFIELDER = "MF", "Midfielder"
        FORWARD = "FW", "Forward"

    class FootPreference(models.TextChoices):
        LEFT = "L", "Left"
        RIGHT = "R", "Right"
        BOTH = "B", "Both"

    position = models.CharField(
        max_length=2, choices=Position.choices, blank=True, null=True
    )
    number = models.IntegerField(null=True, blank=True)
    foot_preference = models.CharField(
        max_length=1, choices=FootPreference.choices, blank=True, null=True
    )
    team = models.ForeignKey("Team", on_delete=models.CASCADE, related_name="players")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["team", "number"], name="unique_player_number_per_team"
            )
        ]


class Team(ModelBase):
    name = models.CharField(max_length=255, null=False, blank=False, unique=True)
    federation = models.CharField(max_length=255, unique=True)
    year_founded = models.IntegerField(null=True, blank=True)
    team_group = models.ForeignKey(
        TeamGroup, on_delete=models.CASCADE, related_name="teams", null=True, blank=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "federation", "year_founded"],
                name="unique_team_federation_year",
            )
        ]

    def __str__(self):
        return self.name


class Coach(Person):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="coaches")


class Stadium(ModelBase):
    name = models.CharField(max_length=255, unique=True)
    city = models.CharField(max_length=255)
    capacity = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return self.name


class Match(ModelBase):
    class Stage(models.TextChoices):
        GROUP = "GROUP", "Group Stage"
        ROUND_OF_32 = "ROUND_OF_32", "Round of 32"
        ROUND_OF_16 = "ROUND_OF_16", "Round of 16"
        QUARTER_FINAL = "QUARTER_FINAL", "Quarter-final"
        SEMI_FINAL = "SEMI_FINAL", "Semi-final"
        THIRD_PLACE = "THIRD_PLACE", "Third place"
        FINAL = "FINAL", "Final"

    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Scheduled"
        LIVE = "LIVE", "Live"
        FINISHED = "FINISHED", "Finished"

    home_team = models.ForeignKey(
        Team, on_delete=models.PROTECT, related_name="home_matches"
    )
    away_team = models.ForeignKey(
        Team, on_delete=models.PROTECT, related_name="away_matches"
    )
    stadium = models.ForeignKey(Stadium, on_delete=models.PROTECT, related_name="matches")
    kickoff = models.DateTimeField()
    stage = models.CharField(max_length=20, choices=Stage.choices)
    team_group = models.ForeignKey(
        TeamGroup, on_delete=models.PROTECT, related_name="matches", null=True, blank=True
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.SCHEDULED
    )
    home_score = models.PositiveSmallIntegerField(null=True, blank=True)
    away_score = models.PositiveSmallIntegerField(null=True, blank=True)
    home_penalties = models.PositiveSmallIntegerField(null=True, blank=True)
    away_penalties = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Matches"
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(home_team=models.F("away_team")),
                name="match_teams_differ",
            )
        ]

    def __str__(self):
        return f"{self.home_team_id} x {self.away_team_id} ({self.stage})"

    @property
    def is_knockout(self):
        return self.stage != self.Stage.GROUP

    @property
    def winner(self):
        if self.status != self.Status.FINISHED:
            return None
        if self.home_score is None or self.away_score is None:
            return None
        if self.home_score != self.away_score:
            return self.home_team if self.home_score > self.away_score else self.away_team
        if self.home_penalties is not None and self.away_penalties is not None:
            if self.home_penalties == self.away_penalties:
                return None
            return (
                self.home_team
                if self.home_penalties > self.away_penalties
                else self.away_team
            )
        return None

    def clean(self):
        super().clean()
        errors = {}
        home_id, away_id = self.home_team_id, self.away_team_id

        if home_id and away_id and home_id == away_id:
            errors["away_team"] = "A seleção visitante deve ser diferente da mandante."

        if self.stage == self.Stage.GROUP:
            if not self.team_group_id:
                errors["team_group"] = "Partidas da fase de grupos exigem um grupo."
            else:
                for field, team in (("home_team", self.home_team if home_id else None),
                                    ("away_team", self.away_team if away_id else None)):
                    if team is not None and team.team_group_id != self.team_group_id:
                        errors[field] = "A seleção deve pertencer ao grupo da partida."

        if self.status == self.Status.FINISHED and (
            self.home_score is None or self.away_score is None
        ):
            errors["home_score"] = "Partidas encerradas exigem o placar."

        home_pen, away_pen = self.home_penalties, self.away_penalties
        if (home_pen is None) != (away_pen is None):
            errors["home_penalties"] = "Os pênaltis de ambas as seleções devem ser informados juntos."
        elif home_pen is not None:
            if not self.is_knockout:
                errors["home_penalties"] = "Pênaltis só são permitidos no mata-mata."
            elif (
                self.home_score is None
                or self.away_score is None
                or self.home_score != self.away_score
            ):
                errors["home_penalties"] = "Pênaltis só são permitidos com placar empatado."
            elif home_pen == away_pen:
                errors["away_penalties"] = "A disputa de pênaltis não pode terminar empatada."

        if errors:
            raise ValidationError(errors)


class Goal(ModelBase):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="goals")
    player = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="goals")
    minute = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(120)]
    )
    stoppage_minute = models.PositiveSmallIntegerField(null=True, blank=True)
    is_penalty = models.BooleanField(default=False)
    is_own_goal = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.player} {self.minute}'"

    @property
    def scoring_team(self):
        team = self.player.team
        if not self.is_own_goal:
            return team
        match = self.match
        return match.away_team if team.id == match.home_team_id else match.home_team

    def clean(self):
        super().clean()
        errors = {}
        if self.is_penalty and self.is_own_goal:
            errors["is_own_goal"] = "Um gol não pode ser pênalti e contra ao mesmo tempo."
        if self.match_id and self.player_id:
            if self.player.team_id not in (
                self.match.home_team_id,
                self.match.away_team_id,
            ):
                errors["player"] = "O jogador deve pertencer a uma das seleções da partida."
        if errors:
            raise ValidationError(errors)

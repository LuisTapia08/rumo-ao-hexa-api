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
    name = models.CharField(max_length=255)
    birth_date = models.DateField()
    height = models.FloatField()
    weight = models.FloatField()
    foot_size = models.FloatField()
    shirt_size = models.CharField(max_length=10)

    def __str__(self):
        return self.name

    class Meta:
        abstract = True


class TeamGroup(ModelBase):
    name = models.CharField(max_length=50)
    description = models.TextField()
    teams = models.ManyToManyField("Team", related_name="team_groups")

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

    position = models.CharField(max_length=2, choices=Position.choices)
    number = models.IntegerField()
    foot_preference = models.CharField(max_length=1, choices=FootPreference.choices)
    team = models.ForeignKey("Team", on_delete=models.CASCADE, related_name="players")


class Team(ModelBase):
    name = models.CharField(max_length=255)
    federation = models.CharField(max_length=255)
    year_founded = models.IntegerField()

    def __str__(self):
        return self.name


class Coach(Person):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="coaches")

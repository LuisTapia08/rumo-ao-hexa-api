from datetime import date, datetime, timezone

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from rest_framework import status
from rest_framework.test import APITestCase

from core import models


class BaseAPITestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.group = models.TeamGroup.objects.create(name="Grupo G", description="Grupo do Brasil")
        cls.brasil = models.Team.objects.create(
            name="Brasil", federation="CBF", year_founded=1914, team_group=cls.group
        )
        cls.servia = models.Team.objects.create(
            name="Sérvia", federation="FSS", year_founded=1919, team_group=cls.group
        )
        cls.stadium = models.Stadium.objects.create(
            name="Lusail Stadium", city="Lusail", capacity=88966
        )
        cls.user = User.objects.create_user(username="tester", password="senha-forte-123")

    def make_match(self, **kwargs):
        data = {
            "home_team": self.brasil,
            "away_team": self.servia,
            "stadium": self.stadium,
            "kickoff": datetime(2022, 11, 24, 19, 0, tzinfo=timezone.utc),
            "stage": models.Match.Stage.GROUP,
            "team_group": self.group,
        }
        data.update(kwargs)
        return models.Match(**data)

    def make_player(self, **kwargs):
        data = {
            "name": "Jogador",
            "birth_date": date(2000, 1, 1),
            "height": 1.80,
            "weight": 75.0,
            "foot_size": 42.0,
            "position": models.Player.Position.FORWARD,
            "number": 10,
            "foot_preference": models.Player.FootPreference.RIGHT,
            "team": self.brasil,
        }
        data.update(kwargs)
        return models.Player.objects.create(**data)


class PermissionTests(BaseAPITestCase):
    def test_anonymous_can_read(self):
        response = self.client.get("/api/team/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_anonymous_cannot_write(self):
        response = self.client.post("/api/team-group/", {"name": "Grupo A", "description": "x", "is_active": True})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_jwt_user_can_write(self):
        token = self.client.post(
            "/api/token/", {"username": "tester", "password": "senha-forte-123"}
        ).data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.post("/api/team-group/", {"name": "Grupo A", "description": "x", "is_active": True})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class PlayerTests(BaseAPITestCase):
    def test_number_is_unique_per_team(self):
        self.make_player(number=10)
        with self.assertRaises(IntegrityError):
            self.make_player(number=10)

    def test_canhotos_returns_only_left_footed_and_is_paginated(self):
        self.make_player(name="Destro", number=1)
        for number in range(2, 9):
            self.make_player(
                name=f"Canhoto {number}",
                number=number,
                foot_preference=models.Player.FootPreference.LEFT,
            )

        response = self.client.get("/api/player/canhotos/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 7)
        self.assertEqual(len(response.data["results"]), 5)
        self.assertTrue(all(p["foot_preference"] == "Left" for p in response.data["results"]))

    def test_filter_by_team_name(self):
        self.make_player()
        response = self.client.get("/api/player/", {"team": "Brasil"})
        self.assertEqual(response.data["count"], 1)
        response = self.client.get("/api/player/", {"team": "Argentina"})
        self.assertEqual(response.data["count"], 0)


class OptionalFieldsTests(BaseAPITestCase):
    def test_player_with_only_name_and_team(self):
        player = models.Player.objects.create(name="Richarlison", team=self.brasil)
        response = self.client.get(f"/api/player/{player.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["position"])
        self.assertIsNone(response.data["shirt_size"])
        self.assertIsNone(response.data["foot_preference"])

    def test_team_without_year_founded(self):
        team = models.Team.objects.create(name="Camarões", federation="FECAFOOT")
        self.assertIsNone(team.year_founded)


class MatchModelTests(BaseAPITestCase):
    def test_valid_group_match(self):
        self.make_match().full_clean()

    def test_same_team_rejected(self):
        with self.assertRaises(ValidationError):
            self.make_match(away_team=self.brasil).full_clean()

    def test_group_stage_requires_group(self):
        with self.assertRaises(ValidationError):
            self.make_match(team_group=None).full_clean()

    def test_group_stage_teams_must_belong_to_group(self):
        outra = models.TeamGroup.objects.create(name="Grupo H", description="x")
        with self.assertRaises(ValidationError):
            self.make_match(team_group=outra).full_clean()

    def test_finished_requires_score(self):
        with self.assertRaises(ValidationError):
            self.make_match(status=models.Match.Status.FINISHED).full_clean()

    def test_penalties_only_in_knockout_draw(self):
        with self.assertRaises(ValidationError):
            self.make_match(
                status=models.Match.Status.FINISHED,
                home_score=1, away_score=1, home_penalties=4, away_penalties=3,
            ).full_clean()
        with self.assertRaises(ValidationError):
            self.make_match(
                stage=models.Match.Stage.ROUND_OF_16, team_group=None,
                status=models.Match.Status.FINISHED,
                home_score=2, away_score=1, home_penalties=4, away_penalties=3,
            ).full_clean()

    def test_penalties_must_be_set_together(self):
        with self.assertRaises(ValidationError):
            self.make_match(
                stage=models.Match.Stage.FINAL, team_group=None,
                status=models.Match.Status.FINISHED,
                home_score=3, away_score=3, home_penalties=4,
            ).full_clean()

    def test_winner(self):
        finished = models.Match.Status.FINISHED
        self.assertEqual(
            self.make_match(status=finished, home_score=2, away_score=0).winner, self.brasil
        )
        self.assertIsNone(self.make_match(status=finished, home_score=1, away_score=1).winner)
        final = self.make_match(
            stage=models.Match.Stage.FINAL, team_group=None, status=finished,
            home_score=3, away_score=3, home_penalties=4, away_penalties=2,
        )
        self.assertEqual(final.winner, self.brasil)
        self.assertTrue(final.is_knockout)
        self.assertIsNone(self.make_match().winner)


class GoalModelTests(BaseAPITestCase):
    def setUp(self):
        self.match = self.make_match()
        self.match.save()
        self.player = self.make_player()

    def make_goal(self, **kwargs):
        data = {"match": self.match, "player": self.player, "minute": 10}
        data.update(kwargs)
        return models.Goal(**data)

    def test_goal_player_must_play_in_match(self):
        outro = models.Team.objects.create(name="Suíça", federation="SFV", team_group=self.group)
        jogador = self.make_player(team=outro, number=9)
        with self.assertRaises(ValidationError):
            self.make_goal(player=jogador).full_clean()

    def test_goal_cannot_be_penalty_and_own_goal(self):
        with self.assertRaises(ValidationError):
            self.make_goal(is_penalty=True, is_own_goal=True).full_clean()

    def test_scoring_team_own_goal(self):
        self.assertEqual(self.make_goal().scoring_team, self.brasil)
        self.assertEqual(self.make_goal(is_own_goal=True).scoring_team, self.servia)

    def test_goal_minute_range(self):
        self.make_goal(minute=1).full_clean()
        for minute in (0, 121):
            with self.assertRaises(ValidationError):
                self.make_goal(minute=minute).full_clean()

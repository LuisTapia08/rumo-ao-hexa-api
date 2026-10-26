from datetime import date

from django.contrib.auth.models import User
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
        cls.user = User.objects.create_user(username="tester", password="senha-forte-123")

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

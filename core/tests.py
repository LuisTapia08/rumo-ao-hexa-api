from datetime import date, datetime, timezone

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from core import models, services


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


class AuthMixin:
    def authenticate(self):
        token = self.client.post(
            "/api/token/", {"username": "tester", "password": "senha-forte-123"}
        ).data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


class MatchAPITests(AuthMixin, BaseAPITestCase):
    def payload(self, **kwargs):
        data = {
            "home_team": self.brasil.id,
            "away_team": self.servia.id,
            "stadium": self.stadium.id,
            "kickoff": "2022-11-24T19:00:00Z",
            "stage": "GROUP",
            "team_group": self.group.id,
        }
        data.update(kwargs)
        return data

    def test_match_list_public_and_shows_names(self):
        match = self.make_match()
        match.save()
        player = self.make_player()
        models.Goal.objects.create(match=match, player=player, minute=10)
        response = self.client.get("/api/match/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data["results"][0]
        self.assertEqual(item["home_team_name"], "Brasil")
        self.assertEqual(item["stadium_name"], "Lusail Stadium")
        self.assertIn("winner", item)
        self.assertIsNone(item["winner"])
        self.assertEqual(len(item["goals"]), 1)
        self.assertEqual(item["goals"][0]["player_name"], "Jogador")
        self.assertEqual(item["goals"][0]["scoring_team"], "Brasil")

    def test_match_list_does_not_have_n_plus_one_queries(self):
        for i in range(3):
            m = self.make_match()
            m.save()
            models.Goal.objects.create(match=m, player=self.make_player(number=20 + i), minute=5)
        with self.assertNumQueries(5):
            self.client.get("/api/match/")

    def test_match_create_requires_auth(self):
        response = self.client.post("/api/match/", self.payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.authenticate()
        response = self.client.post("/api/match/", self.payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_match_invalid_returns_400(self):
        self.authenticate()
        response = self.client.post(
            "/api/match/",
            self.payload(stage="FINAL", team_group=None, home_penalties=3),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("home_penalties", response.data)

    def test_match_partial_update_validates_merged_values(self):
        match = self.make_match()
        match.save()
        self.authenticate()
        response = self.client.patch(
            f"/api/match/{match.id}/", {"home_penalties": 3, "away_penalties": 2}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_match_filter_team_case_insensitive(self):
        self.make_match().save()
        response = self.client.get("/api/match/?team=brasil")
        self.assertEqual(response.data["count"], 1)
        response = self.client.get("/api/match/?team=Argentina")
        self.assertEqual(response.data["count"], 0)

    def test_match_filter_stage_and_kickoff(self):
        self.make_match().save()
        self.assertEqual(self.client.get("/api/match/?stage=GROUP").data["count"], 1)
        self.assertEqual(self.client.get("/api/match/?stage=FINAL").data["count"], 0)
        self.assertEqual(self.client.get("/api/match/?kickoff_after=2022-11-25").data["count"], 0)
        self.assertEqual(self.client.get("/api/match/?kickoff_after=2022-11-24").data["count"], 1)
        self.assertEqual(self.client.get("/api/match/?kickoff_before=2022-11-23").data["count"], 0)

    def test_match_winner_is_team_name(self):
        match = self.make_match(
            status=models.Match.Status.FINISHED, home_score=2, away_score=0
        )
        match.save()
        item = self.client.get("/api/match/").data["results"][0]
        self.assertEqual(item["winner"], "Brasil")


class StadiumAPITests(AuthMixin, BaseAPITestCase):
    def test_stadium_list_and_filter(self):
        self.assertEqual(self.client.get("/api/stadium/").data["count"], 1)
        self.assertEqual(self.client.get("/api/stadium/?city=lusail").data["count"], 1)
        self.assertEqual(self.client.get("/api/stadium/?city=Doha").data["count"], 0)


class GoalAPITests(AuthMixin, BaseAPITestCase):
    def setUp(self):
        self.match = self.make_match()
        self.match.save()
        self.player = self.make_player()

    def test_goal_create_ok(self):
        self.authenticate()
        response = self.client.post(
            "/api/goal/",
            {"match": self.match.id, "player": self.player.id, "minute": 12},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_goal_invalid_player_returns_400(self):
        outsider_team = models.Team.objects.create(name="Gana", federation="GFA")
        outsider = self.make_player(name="Fora", team=outsider_team, number=7)
        self.authenticate()
        response = self.client.post(
            "/api/goal/",
            {"match": self.match.id, "player": outsider.id, "minute": 12},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_goal_filter_team_and_own_goal(self):
        models.Goal.objects.create(match=self.match, player=self.player, minute=5)
        models.Goal.objects.create(
            match=self.match, player=self.player, minute=50, is_own_goal=True
        )
        self.assertEqual(self.client.get("/api/goal/?team=brasil").data["count"], 2)
        self.assertEqual(self.client.get("/api/goal/?team=Sérvia").data["count"], 0)
        self.assertEqual(self.client.get("/api/goal/?is_own_goal=true").data["count"], 1)
        self.assertEqual(self.client.get(f"/api/goal/?match={self.match.id}").data["count"], 2)


class StandingsTests(BaseAPITestCase):
    def setUp(self):
        self.a = self.brasil
        self.b = self.servia
        self.c = models.Team.objects.create(name="Suíça", federation="SFV", team_group=self.group)
        self.d = models.Team.objects.create(name="Camarões", federation="FECAFOOT", team_group=self.group)

    def finished(self, home, away, home_score, away_score, **kwargs):
        match = self.make_match(
            home_team=home,
            away_team=away,
            home_score=home_score,
            away_score=away_score,
            status=models.Match.Status.FINISHED,
            **kwargs,
        )
        match.save()
        return match

    def test_standings_points_and_order(self):
        from core.services import group_standings

        self.finished(self.a, self.b, 2, 0)
        self.finished(self.a, self.c, 1, 1)
        self.finished(self.d, self.b, 3, 0)

        table = group_standings(self.group)

        self.assertEqual(
            [row["team"] for row in table], ["Brasil", "Camarões", "Suíça", "Sérvia"]
        )
        self.assertEqual([row["points"] for row in table], [4, 3, 1, 0])
        self.assertEqual(table[0]["goal_difference"], 2)
        self.assertEqual(table[0]["team_id"], self.a.id)
        self.assertEqual(table[0]["played"], 2)
        self.assertEqual((table[0]["won"], table[0]["drawn"], table[0]["lost"]), (1, 1, 0))

    def test_standings_tiebreak_goal_difference_then_goals_for(self):
        from core.services import group_standings

        # A e D: 3 pontos; saldo igual (+1); D com mais gols pró (3 x 2)
        self.finished(self.a, self.b, 1, 0)
        self.finished(self.d, self.c, 3, 2)
        # B e C: 0 pontos; saldos -1 e -1; gols pró B=0, C=2 -> C antes de B
        table = group_standings(self.group)
        self.assertEqual(
            [row["team"] for row in table], ["Camarões", "Brasil", "Suíça", "Sérvia"]
        )

    def test_standings_tiebreak_goal_difference(self):
        from core.services import group_standings

        self.finished(self.a, self.b, 1, 0)
        self.finished(self.d, self.c, 3, 0)
        table = group_standings(self.group)
        self.assertEqual([row["team"] for row in table][:2], ["Camarões", "Brasil"])

    def test_standings_ignores_unfinished_and_knockout(self):
        from core.services import group_standings

        self.make_match(
            home_team=self.a, away_team=self.b, home_score=5, away_score=0
        ).save()
        self.finished(self.a, self.b, 4, 0, stage=models.Match.Stage.ROUND_OF_16, team_group=None)

        table = group_standings(self.group)

        self.assertTrue(all(row["played"] == 0 for row in table))

    def test_standings_empty_group_lists_teams_with_zeros(self):
        from core.services import group_standings

        table = group_standings(self.group)

        self.assertEqual(len(table), 4)
        self.assertEqual([row["team"] for row in table], ["Brasil", "Camarões", "Sérvia", "Suíça"])
        for row in table:
            self.assertEqual(row["points"], 0)
            self.assertEqual(row["goals_for"], 0)

    def test_classificacao_endpoint(self):
        self.finished(self.a, self.b, 2, 0)

        response = self.client.get(f"/api/team-group/{self.group.id}/classificacao/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)
        self.assertEqual(response.data[0]["team"], "Brasil")


class TopScorersTests(BaseAPITestCase):
    def setUp(self):
        self.match = self.make_match()
        self.match.save()

    def test_top_scorers_ignores_own_goals_and_counts_penalties(self):
        from core.services import top_scorers

        x = self.make_player(name="X", number=9)
        y = self.make_player(name="Y", number=11)
        models.Goal.objects.create(match=self.match, player=x, minute=10)
        models.Goal.objects.create(match=self.match, player=x, minute=20, is_penalty=True)
        models.Goal.objects.create(match=self.match, player=y, minute=30)
        models.Goal.objects.create(match=self.match, player=y, minute=40, is_own_goal=True)
        own_only = self.make_player(name="Z", number=3)
        models.Goal.objects.create(match=self.match, player=own_only, minute=50, is_own_goal=True)

        result = list(top_scorers(models.Goal.objects.all()))

        self.assertEqual([p.name for p in result], ["X", "Y"])
        self.assertEqual((result[0].goals_count, result[0].penalties_count), (2, 1))
        self.assertEqual((result[1].goals_count, result[1].penalties_count), (1, 0))

    def test_artilheiros_endpoint_paginated_and_filter_team(self):
        for number in range(1, 8):
            player = self.make_player(name=f"Brasileiro {number}", number=number)
            models.Goal.objects.create(match=self.match, player=player, minute=number)
        sérvio = self.make_player(name="Mitrovic", number=9, team=self.servia)
        models.Goal.objects.create(match=self.match, player=sérvio, minute=60)
        models.Goal.objects.create(match=self.match, player=sérvio, minute=61)

        response = self.client.get("/api/player/artilheiros/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 8)
        self.assertEqual(len(response.data["results"]), 5)
        self.assertEqual(
            response.data["results"][0],
            {"player": "Mitrovic", "team": "Sérvia", "goals": 2, "penalties": 0},
        )

        response = self.client.get("/api/player/artilheiros/", {"team": "brasil"})
        self.assertEqual(response.data["count"], 7)


class SeedWorldCup2022Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_worldcup2022", verbosity=0)

    def counts(self):
        return (
            models.Match.objects.count(),
            models.Goal.objects.count(),
            models.Team.objects.count(),
            models.TeamGroup.objects.count(),
            models.Stadium.objects.count(),
            models.Coach.objects.count(),
        )

    def test_counts(self):
        self.assertEqual(self.counts(), (64, 172, 32, 8, 8, 32))

    def test_goals_match_scores(self):
        for match in models.Match.objects.prefetch_related("goals"):
            home = sum(1 for g in match.goals.all() if g.scoring_team == match.home_team)
            away = sum(1 for g in match.goals.all() if g.scoring_team == match.away_team)
            self.assertEqual(
                (home, away),
                (match.home_score, match.away_score),
                f"{match.home_team} x {match.away_team}",
            )

    def test_top_scorer_is_mbappe_with_8(self):
        top = services.top_scorers(models.Goal.objects.all()).first()
        self.assertEqual(top.name, "Kylian Mbappé")
        self.assertEqual(top.goals_count, 8)

    def test_final_argentina_wins_on_penalties(self):
        final = models.Match.objects.get(stage=models.Match.Stage.FINAL)
        self.assertEqual((final.home_score, final.away_score), (3, 3))
        self.assertEqual((final.home_penalties, final.away_penalties), (4, 2))
        self.assertEqual(final.winner.name, "Argentina")

    def test_brasil_first_in_group_g(self):
        group = models.TeamGroup.objects.get(name="Grupo G")
        first = services.group_standings(group)[0]
        self.assertEqual(first["team"], "Brasil")
        self.assertEqual(first["points"], 6)

    def test_idempotent(self):
        before = self.counts()
        call_command("seed_worldcup2022", verbosity=0)
        self.assertEqual(self.counts(), before)


class SeedWorldCup2022ConflictTests(TestCase):
    def test_conflicting_local_data_raises_and_rolls_back(self):
        models.Team.objects.create(name="Seleção X", federation="CBF")
        with self.assertRaises(CommandError) as ctx:
            call_command("seed_worldcup2022", verbosity=0)
        self.assertIn("--reset", str(ctx.exception))
        self.assertIn("UNIQUE constraint failed", str(ctx.exception))
        self.assertEqual(models.Match.objects.count(), 0)
        self.assertEqual(models.Team.objects.count(), 1)

    def test_invalid_data_raises_command_error_and_rolls_back(self):
        import json
        import tempfile
        from pathlib import Path

        from django.test import override_settings

        bad = {
            "groups": [{"name": "Grupo A", "teams": ["A", "B"]}],
            "teams": [
                {"name": "A", "federation": "FA1", "coach": "Tec A"},
                {"name": "B", "federation": "FB1", "coach": "Tec B"},
            ],
            "stadiums": [{"name": "Est", "city": "Cidade", "capacity": 1000}],
            "matches": [
                {
                    "stage": "GROUP", "group": "Grupo A",
                    "kickoff": "2022-11-20T19:00:00+03:00",
                    "home": "A", "away": "A", "stadium": "Est",
                    "home_score": 0, "away_score": 0,
                    "home_penalties": None, "away_penalties": None,
                    "goals": [],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "data").mkdir()
            with open(Path(tmp) / "data" / "worldcup2022.json", "w", encoding="utf-8") as f:
                json.dump(bad, f)
            with override_settings(BASE_DIR=Path(tmp)):
                with self.assertRaises(CommandError) as ctx:
                    call_command("seed_worldcup2022", verbosity=0)
        self.assertIn("diferente", str(ctx.exception))
        self.assertIn("--reset", str(ctx.exception))
        self.assertEqual(models.Team.objects.count(), 0)
        self.assertEqual(models.TeamGroup.objects.count(), 0)
        self.assertEqual(models.Match.objects.count(), 0)


class DocsTests(TestCase):
    def test_root_redirects_to_docs(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/api/docs/")

    def test_swagger_ui_is_public(self):
        self.assertEqual(self.client.get("/api/docs/").status_code, 200)

    def test_schema_is_public(self):
        self.assertEqual(self.client.get("/api/schema/").status_code, 200)
# Finalização da API Rumo ao Hexa — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completar a API com partidas, estádios, gols, classificação, artilharia, dados reais da Copa 2022, Swagger, Docker, deploy no Render e CI.

**Architecture:** Novos models no app `core`, seguindo o padrão `ModelBase` + `BaseViewSet` + `FilterSet` existente. Cálculos (classificação, artilharia) em `core/services.py` como funções puras sobre querysets. Dados carregados por um management command a partir de `data/worldcup2022.json`.

**Tech Stack:** Python 3.14, Django 6.0, DRF 3.17, simplejwt, django-filter, drf-spectacular, django-cors-headers, dj-database-url, whitenoise, gunicorn, Docker, Render, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-26-finalizacao-api-design.md`

## Global Constraints

- Testes com `python manage.py test` (APITestCase), nada de pytest.
- Todo ViewSet novo herda de `BaseViewSet` (leitura pública, escrita com JWT) e tem queryset com `.order_by(...)` explícito.
- Nomes de rotas e ações em português onde já é o padrão (`canhotos`, `artilheiros`, `classificacao`); campos de model em inglês.
- Nomes de seleções e grupos no seed em português (`Brasil`, `França`, `Grupo G`).
- Dependências fixadas com versão exata em `requirements.txt`.
- Commits terminam com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Arquivos em UTF-8 sem BOM (não editar arquivos com acento via `Set-Content` do PowerShell 5.1).

## Review Focus

- Partida de mata-mata empatada com pênaltis de só um lado (`home_penalties=4`, `away_penalties=None`) → 400, não 500. Teste na Task 2.
- Gol cujo jogador não pertence a nenhum dos dois times da partida → 400. Teste na Task 2.
- Classificação de grupo sem nenhuma partida encerrada → todas as seleções com zeros, não lista vazia nem erro. Teste na Task 4.
- Filtro `?team=brasil` em partidas (caixa diferente) → encontra as partidas do Brasil (`iexact`). Teste na Task 3.
- Rodar o seed sobre um banco local que já tem uma seleção com a mesma federação e outro nome → `CommandError` com mensagem sugerindo `--reset`, sem gravação parcial. Teste na Task 5.

---

### Task 1: Campos opcionais em Person, Player e Team

**Files:**
- Modify: `core/models.py`, `core/serializers.py`
- Create: migração gerada `core/migrations/0007_*.py`
- Test: `core/tests.py`

**Interfaces:**
- Produces: `Player` criável só com `name` e `team`; `Team` criável sem `year_founded`.

- [ ] **Step 1: Testes que falham**

```python
class OptionalFieldsTests(BaseAPITestCase):
    def test_player_with_only_name_and_team(self):
        player = models.Player.objects.create(name="Richarlison", team=self.brasil)
        response = self.client.get(f"/api/player/{player.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["position"])
        self.assertIsNone(response.data["shirt_size"])
        self.assertIsNone(response.data["foot_preference"])

    def test_team_without_year_founded(self):
        team = models.Team.objects.create(name="Sérvia", federation="FSS")
        self.assertIsNone(team.year_founded)
```

- [ ] **Step 2:** `python manage.py test core.tests.OptionalFieldsTests` → FAIL (IntegrityError NOT NULL).
- [ ] **Step 3:** Em `Person`, `birth_date`, `height`, `weight`, `foot_size` com `null=True, blank=True`. Em `Player`, `position`, `foot_preference` com `blank=True, null=True`; `number` com `null=True, blank=True`. Em `Team`, `year_founded` com `null=True, blank=True`. Nos serializers, só chamar `get_*_display()` quando o campo não for vazio; caso contrário devolver `None`. `python manage.py makemigrations core -n optional_person_fields`.
- [ ] **Step 4:** `python manage.py test` → todos passam.
- [ ] **Step 5:** Commit `Make physical and squad fields optional`.

---

### Task 2: Models Stadium, Match e Goal com validações

**Files:**
- Modify: `core/models.py`, `core/admin.py`
- Create: migração `core/migrations/0008_*.py`
- Test: `core/tests.py`

**Interfaces:**
- Produces:
  - `Stadium(name, city, capacity)`
  - `Match.Stage` (`GROUP`, `ROUND_OF_32`, `ROUND_OF_16`, `QUARTER_FINAL`, `SEMI_FINAL`, `THIRD_PLACE`, `FINAL`), `Match.Status` (`SCHEDULED`, `LIVE`, `FINISHED`)
  - `Match(home_team, away_team, stadium, kickoff, stage, team_group, status, home_score, away_score, home_penalties, away_penalties)`; `Match.clean()`; `Match.winner -> Team | None`; `Match.is_knockout -> bool`
  - `Goal(match, player, minute, stoppage_minute, is_penalty, is_own_goal)`; `Goal.clean()`; `Goal.scoring_team -> Team`
  - related names: `Team.home_matches`, `Team.away_matches`, `Match.goals`, `Player.goals`

- [ ] **Step 1: Testes que falham** (`MatchModelTests`, `GoalModelTests`). Helper `make_match(**kwargs)` em `BaseAPITestCase` criando partida de grupo Brasil x Sérvia no `Grupo G`. Cada um chama `full_clean()` e espera `ValidationError`, exceto os de sucesso:
  - `test_same_team_rejected` (home == away)
  - `test_group_stage_requires_group`
  - `test_group_stage_teams_must_belong_to_group`
  - `test_finished_requires_score`
  - `test_penalties_only_in_knockout_draw` (grupo 1x1 com pênaltis → erro; oitavas 2x1 com pênaltis → erro)
  - `test_penalties_must_be_set_together` (só `home_penalties=4` → erro)
  - `test_winner`: grupo 2x0 → mandante; grupo 1x1 → `None`; final 3x3 pênaltis 4x2 → mandante; agendada → `None`
  - `test_goal_player_must_play_in_match` (jogador de time de fora → erro)
  - `test_goal_cannot_be_penalty_and_own_goal`
  - `test_scoring_team_own_goal` (gol contra de jogador do Brasil → `scoring_team == servia`)
  - `test_goal_minute_range` (0 e 121 → erro)
- [ ] **Step 2:** Rodar os testes → FAIL (models inexistentes).
- [ ] **Step 3:** Implementar os models conforme a tabela do spec, `CheckConstraint(condition=~Q(home_team=F("away_team")), name="match_teams_differ")`, validações em `clean()` lançando `ValidationError({campo: msg})`. Registrar os três no admin. `makemigrations core -n matches_stadiums_goals`.
- [ ] **Step 4:** `python manage.py test` → passam.
- [ ] **Step 5:** Commit `Add stadium, match and goal models`.

---

### Task 3: API de estádios, partidas e gols

**Files:**
- Modify: `core/serializers.py`, `core/filters.py`, `core/views.py`, `setup/urls.py`
- Test: `core/tests.py`

**Interfaces:**
- Consumes: models da Task 2.
- Produces: rotas `/api/stadium/`, `/api/match/`, `/api/goal/`; `StadiumFilter`, `MatchFilter`, `GoalFilter`; `GoalNestedSerializer` (campos `id, player, player_name, minute, stoppage_minute, is_penalty, is_own_goal, scoring_team`).

- [ ] **Step 1: Testes que falham** (`MatchAPITests`, `GoalAPITests`):
  - `test_match_list_public_and_shows_names`: GET `/api/match/` anônimo → 200; `results[0]["home_team_name"] == "Brasil"`, `"stadium_name"`, `"winner"`, `"goals"` presentes.
  - `test_match_create_requires_auth` → 401 anônimo; 201 com JWT.
  - `test_match_invalid_returns_400` (penalties de um lado só, via POST autenticado) → 400.
  - `test_match_filter_team_case_insensitive`: `?team=brasil` retorna a partida; `?team=Argentina` → `count == 0`.
  - `test_match_filter_stage_and_kickoff`: `?stage=GROUP`, `?kickoff_after=2022-11-25` filtram corretamente.
  - `test_goal_invalid_player_returns_400`.
  - `test_goal_filter_team_and_own_goal`.
- [ ] **Step 2:** Rodar → FAIL (404).
- [ ] **Step 3:** Serializers herdando de `ModelSerializer` do projeto; `MatchSerializer` com campos de leitura `home_team_name`, `away_team_name`, `stadium_name`, `winner` (nome ou `None`), `goals` (nested read-only) e `validate()` que monta a instância e chama `clean()`, convertendo `django.core.exceptions.ValidationError` em `serializers.ValidationError`; o mesmo para `GoalSerializer`. `MatchFilter.team`: `CharFilter(method=...)` com `Q(home_team__name__iexact=v) | Q(away_team__name__iexact=v)`; `kickoff_after/before` com `gte/lte` em `kickoff`. `GoalFilter.team` em `player__team__name` `iexact`. ViewSets com `select_related`/`prefetch_related("goals__player__team")` e `order_by("kickoff", "id")` para partidas, `order_by("match__kickoff", "minute", "stoppage_minute", "id")` para gols. Registrar rotas.
- [ ] **Step 4:** `python manage.py test` → passam.
- [ ] **Step 5:** Commit `Add stadium, match and goal endpoints`.

---

### Task 4: Classificação e artilharia

**Files:**
- Create: `core/services.py`
- Modify: `core/views.py`, `core/serializers.py`
- Test: `core/tests.py`

**Interfaces:**
- Consumes: models da Task 2.
- Produces:
  - `group_standings(group: TeamGroup) -> list[dict]` com chaves `team, team_id, points, played, won, drawn, lost, goals_for, goals_against, goal_difference`
  - `top_scorers(goals: QuerySet[Goal]) -> QuerySet[Player]` anotado com `goals_count` e `penalties_count`, excluindo gol contra
  - ações `TeamGroupViewSet.classificacao` (detail) e `PlayerViewSet.artilheiros` (list)

- [ ] **Step 1: Testes que falham** (`StandingsTests`, `TopScorersTests`), montando um grupo de 4 times:
  - `test_standings_points_and_order`: A vence B 2x0, A empata C 1x1, D vence B 3x0 → ordem `[A(4), D(3), C(1), B(0)]`, `A.goal_difference == 2`.
  - `test_standings_tiebreak_goal_difference_then_goals_for`
  - `test_standings_ignores_unfinished_and_knockout`
  - `test_standings_empty_group_lists_teams_with_zeros`
  - `test_classificacao_endpoint`: GET `/api/team-group/{id}/classificacao/` anônimo → 200, lista com 4 itens.
  - `test_top_scorers_ignores_own_goals_and_counts_penalties`: jogador X 2 gols (1 pênalti), Y 1 gol + 1 contra → `[X(2, 1 pên.), Y(1)]`.
  - `test_artilheiros_endpoint_paginated_and_filter_team`.
- [ ] **Step 2:** Rodar → FAIL.
- [ ] **Step 3:** `group_standings`: carrega times do grupo e partidas `FINISHED` com `stage=GROUP` e `team_group=group`; acumula em dict por time; ordena por `(-points, -goal_difference, -goals_for, name)`. `top_scorers`: `Player.objects.filter(goals__in=goals.filter(is_own_goal=False)).annotate(goals_count=Count("goals"), penalties_count=Count("goals", filter=Q(goals__is_penalty=True))).order_by("-goals_count", "name")` — atenção para os filtros do annotate também excluírem gol contra. Action `artilheiros` aplica filtro opcional `?team=` (nome `iexact`) e paginação; serializer simples `TopScorerSerializer(player, team, goals, penalties)`.
- [ ] **Step 4:** `python manage.py test` → passam.
- [ ] **Step 5:** Commit `Add group standings and top scorers`.

---

### Task 5: Dados da Copa 2022 e comando de seed

**Files:**
- Create: `data/worldcup2022.json`, `core/management/__init__.py`, `core/management/commands/__init__.py`, `core/management/commands/seed_worldcup2022.py`
- Test: `core/tests.py`

**Interfaces:**
- Consumes: todos os models.
- Produces: comando `seed_worldcup2022 [--reset]`; formato do JSON:

```json
{
  "groups": [{"name": "Grupo A", "teams": ["Catar", "Equador", "Senegal", "Holanda"]}],
  "teams": [{"name": "Brasil", "federation": "CBF", "coach": "Tite"}],
  "stadiums": [{"name": "Lusail Iconic Stadium", "city": "Lusail", "capacity": 88966}],
  "matches": [{
    "stage": "FINAL", "group": null, "kickoff": "2022-12-18T18:00:00+03:00",
    "home": "Argentina", "away": "França", "stadium": "Lusail Iconic Stadium",
    "home_score": 3, "away_score": 3, "home_penalties": 4, "away_penalties": 2,
    "goals": [{"player": "Lionel Messi", "team": "Argentina", "minute": 23, "stoppage_minute": null, "is_penalty": true, "is_own_goal": false}]
  }]
}
```

- [ ] **Step 1: Gerar `data/worldcup2022.json`** com um script descartável (scratchpad, não versionado) a partir de `https://raw.githubusercontent.com/openfootball/worldcup.json/master/2022/worldcup.json`: `"Matchday N"` → `GROUP`; `Round of 16`, `Quarter-finals`, `Semi-finals`, `Match for third place`, `Final` → stages correspondentes; placar = `et` se existir, senão `ft`; pênaltis = `p`; `"90+8"` → `minute=90, stoppage_minute=8`; `ground` `"Nome, Cidade"` → stadium/city; `goal.team` = time do jogador (para gol contra, o time oposto ao lado em que a fonte listou o gol — conferir os 2 casos: Nayef Aguerd/Marrocos, Enzo Fernández/Argentina). Traduzir as 32 seleções para português. Complementar federações (sigla oficial; Austrália = `Football Australia` para não colidir com `FA` da Inglaterra), técnicos e capacidades: Lusail 88966, Al Bayt 68895, Khalifa International 45857, Education City 44667, Ahmad bin Ali 45032, Al Janoub 44325, Al Thumama 44400, Stadium 974 44089.
- [ ] **Step 2: Testes que falham** (`SeedWorldCup2022Tests`, usando `call_command("seed_worldcup2022")` em `setUpTestData`):
  - `test_counts`: 64 partidas, 172 gols, 32 seleções, 8 grupos, 8 estádios, 32 técnicos.
  - `test_goals_match_scores`: para cada partida, gols creditados a cada lado (`scoring_team`) == placar.
  - `test_top_scorer_is_mbappe_with_8`
  - `test_final_argentina_wins_on_penalties`: final 3x3, pênaltis 4x2, `winner.name == "Argentina"`.
  - `test_brasil_first_in_group_g`: `group_standings(Grupo G)[0]["team"] == "Brasil"` com 6 pontos.
  - `test_idempotent`: rodar de novo mantém as contagens.
  - `test_conflicting_local_data_raises_and_rolls_back`: (classe separada, banco vazio) criar `Team(name="Seleção X", federation="CBF")` → `call_command` levanta `CommandError` cuja mensagem contém `--reset`; nenhuma partida criada.
- [ ] **Step 3:** Rodar → FAIL.
- [ ] **Step 4:** Implementar o comando: lê `settings.BASE_DIR / "data" / "worldcup2022.json"`, tudo dentro de `transaction.atomic()`; `--reset` apaga na ordem Goal, Match, Coach, Player, Team, Stadium, TeamGroup; `update_or_create` por chave natural (grupo por nome, seleção por nome, estádio por nome, técnico por (nome, time), jogador por (nome, time), partida por (home, away, stage), gol por (match, player, minute, stoppage_minute)); grupos com descrição `"Fase de grupos da Copa do Mundo FIFA 2022"`; `IntegrityError` vira `CommandError("... rode com --reset")`; imprime resumo das contagens.
- [ ] **Step 5:** `python manage.py test` → passam. Rodar `python manage.py seed_worldcup2022` no banco local e conferir `/api/team-group/` manualmente.
- [ ] **Step 6:** Commit `Add World Cup 2022 dataset and seed command`.

---

### Task 6: Swagger, configuração por ambiente e CORS

**Files:**
- Modify: `setup/settings.py`, `setup/urls.py`, `requirements.txt`, `.gitignore`
- Test: `core/tests.py`

**Interfaces:**
- Produces: `/api/schema/`, `/api/docs/`, redirect `/` → `/api/docs/`; variáveis `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DATABASE_URL`, `CORS_ALLOWED_ORIGINS`.

- [ ] **Step 1: Testes que falham** (`DocsTests`): `/` → 302 para `/api/docs/`; `/api/docs/` → 200; `/api/schema/` → 200.
- [ ] **Step 2:** Rodar → FAIL.
- [ ] **Step 3:** `pip install drf-spectacular django-cors-headers dj-database-url whitenoise gunicorn` e fixar versões no `requirements.txt`. Settings: `SECRET_KEY = os.environ.get("SECRET_KEY", <chave dev atual>)`; `DEBUG = os.environ.get("DEBUG", "True") == "True"`; listas lidas de env separadas por vírgula (`ALLOWED_HOSTS` default `localhost,127.0.0.1`); `DATABASES = {"default": dj_database_url.config(default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}`; `corsheaders` + `CorsMiddleware` antes de `CommonMiddleware`; `WhiteNoiseMiddleware` logo após `SecurityMiddleware`; `STATIC_ROOT = BASE_DIR / "staticfiles"`; `DEFAULT_SCHEMA_CLASS` do spectacular e `SPECTACULAR_SETTINGS` com título "Rumo ao Hexa API", descrição e versão `1.0.0`. Adicionar `staticfiles/` ao `.gitignore`.
- [ ] **Step 4:** `python manage.py test` → passam; `python manage.py spectacular --validate --fail-on-warn --file NUL` → sem warnings (corrigir com `@extend_schema` nas actions customizadas se necessário).
- [ ] **Step 5:** Commit `Add Swagger docs and environment-based settings`.

---

### Task 7: Docker, Render e CI

**Files:**
- Create: `Dockerfile`, `.dockerignore`, `docker-entrypoint.sh`, `render.yaml`, `.github/workflows/tests.yml`, `.gitattributes`

**Interfaces:**
- Consumes: settings da Task 6, comando da Task 5.

- [ ] **Step 1:** `Dockerfile` a partir de `python:3.14-slim`, instala `requirements.txt`, copia o projeto, `collectstatic --noinput` no build, `EXPOSE 8000`, `ENTRYPOINT ["./docker-entrypoint.sh"]`. Entrypoint (`sh`, `set -e`): `migrate --noinput`, `seed_worldcup2022`, `createsuperuser --noinput` só se `DJANGO_SUPERUSER_USERNAME` estiver definido (ignorando erro de usuário existente), `exec gunicorn setup.wsgi --bind 0.0.0.0:${PORT:-8000}`. `.gitattributes` com `*.sh text eol=lf` para o entrypoint não quebrar no Linux. `.dockerignore`: `.venv`, `.git`, `db.sqlite3`, `__pycache__`, `staticfiles`.
- [ ] **Step 2:** `render.yaml`: serviço `web`, `runtime: docker`, `plan: free`, `healthCheckPath: /api/docs/`, env `DEBUG=False`, `SECRET_KEY` com `generateValue: true`, `ALLOWED_HOSTS=.onrender.com`, `CSRF_TRUSTED_ORIGINS=https://*.onrender.com`, `DJANGO_SUPERUSER_USERNAME`/`PASSWORD`/`EMAIL` com `sync: false`.
- [ ] **Step 3:** `.github/workflows/tests.yml`: em `push` e `pull_request`, `ubuntu-latest`, `actions/setup-python` 3.14, `pip install -r requirements.txt`, `python manage.py test`.
- [ ] **Step 4: Verificar.** Se Docker estiver instalado: `docker build -t rumo-ao-hexa-api .` e `docker run -p 8000:8000 -e DEBUG=False -e ALLOWED_HOSTS=localhost rumo-ao-hexa-api`, depois `/api/docs/` → 200 e `/api/match/` com 64 partidas. Sem Docker: simular localmente com `DEBUG=False` + `collectstatic` + `gunicorn` não roda no Windows, então rodar `python manage.py check --deploy` com as variáveis de produção e registrar que o build Docker fica validado pelo Render.
- [ ] **Step 5:** Commit `Add Docker, Render blueprint and CI workflow`.

---

### Task 8: README final

**Files:**
- Modify: `README.md`

- [ ] **Step 1:** Atualizar: selo do CI (`https://github.com/LuisTapia08/rumo-ao-hexa-api/actions/workflows/tests.yml/badge.svg`), link da demo (placeholder explícito "adicione após o deploy" só se o deploy ainda não existir), Swagger, modelo de dados com Stadium/Match/Goal, novos endpoints e filtros, exemplos (`/api/match/?team=Brasil`, `/api/team-group/{id}/classificacao/`, `/api/player/artilheiros/`), seed, Docker, passo a passo de deploy no Render (New → Blueprint → conectar repositório), limitações (desempate sem confronto direto/fair play; jogadores só com dados básicos; banco efêmero no plano grátis), créditos de dados (openfootball, CC0) e da base do projeto.
- [ ] **Step 2:** Conferir que todo endpoint e filtro citado existe (`python manage.py show_urls` não existe; conferir contra `setup/urls.py` e `core/filters.py`) e que os comandos do README rodam.
- [ ] **Step 3:** Commit `Update README for the finished API`.

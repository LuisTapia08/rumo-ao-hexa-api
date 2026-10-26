# Finalização da API Rumo ao Hexa — Design

Data: 2026-10-26
Status: aprovado em conversa, aguardando revisão do documento

## Objetivo

Projeto de portfólio: demonstrar uma API REST bem construída (código limpo, testes, documentação, deploy com link público). Não há requisito de tempo real nem integração com API externa de placares.

Critério de sucesso: um visitante abre o link público, cai na documentação Swagger e consegue consultar partidas, classificação dos grupos e artilharia da Copa de 2022 com dados reais e corretos.

## Fora de escopo

- Geração automática do chaveamento do mata-mata (a fase é só um atributo da partida).
- Desempate por confronto direto e fair play na classificação.
- Front-end.

## 1. Models

Todos herdam de `ModelBase` (`id`, `is_active`, `created_at`, `updated_at`).

### Stadium
| Campo | Tipo | Regras |
| --- | --- | --- |
| `name` | CharField(255) | único |
| `city` | CharField(255) | |
| `capacity` | PositiveIntegerField | opcional |

### Match
| Campo | Tipo | Regras |
| --- | --- | --- |
| `home_team` | FK Team (PROTECT, related_name `home_matches`) | |
| `away_team` | FK Team (PROTECT, related_name `away_matches`) | diferente de `home_team` (CheckConstraint) |
| `stadium` | FK Stadium (PROTECT) | |
| `kickoff` | DateTimeField | |
| `stage` | choices: `GROUP`, `ROUND_OF_32`, `ROUND_OF_16`, `QUARTER_FINAL`, `SEMI_FINAL`, `THIRD_PLACE`, `FINAL` | |
| `team_group` | FK TeamGroup (PROTECT), opcional | obrigatório se `stage == GROUP`; ambas as seleções devem pertencer ao grupo |
| `status` | choices: `SCHEDULED`, `LIVE`, `FINISHED` | default `SCHEDULED` |
| `home_score`, `away_score` | PositiveSmallIntegerField, opcional | obrigatórios se `FINISHED`; placar final incluindo prorrogação |
| `home_penalties`, `away_penalties` | PositiveSmallIntegerField, opcional | só permitidos em mata-mata com placar empatado; preenchidos juntos |

Validações em `Match.clean()`, chamadas também pelo serializer.

Propriedade `winner`: seleção vencedora considerando pênaltis; `None` se não encerrada ou empate na fase de grupos.

### Goal
| Campo | Tipo | Regras |
| --- | --- | --- |
| `match` | FK Match (CASCADE, related_name `goals`) | |
| `player` | FK Player (PROTECT, related_name `goals`) | o time do jogador deve ser um dos times da partida |
| `minute` | PositiveSmallIntegerField | 1–120 |
| `stoppage_minute` | PositiveSmallIntegerField, opcional | acréscimos (ex.: 90+8 → minute=90, stoppage=8) |
| `is_penalty` | BooleanField | default False |
| `is_own_goal` | BooleanField | default False; não pode ser pênalti ao mesmo tempo |

Propriedade `scoring_team`: time do jogador, ou o adversário se `is_own_goal`. Gols de disputa de pênaltis não são `Goal`.

### Ajustes nos models existentes
- `Person`: `birth_date`, `height`, `weight`, `foot_size` passam a ser opcionais.
- `Player`: `position`, `number`, `foot_preference` passam a ser opcionais. Constraint de número único por seleção continua (NULL não conflita).
- `Team`: `year_founded` passa a ser opcional.
- Serializers que usam `get_*_display()` devolvem `null` quando o campo está vazio.

Motivo: não há fonte confiável para esses dados dos ~100 jogadores que marcaram em 2022; preferimos vazio a inventado.

## 2. Endpoints

Leitura pública, escrita com JWT (`BaseViewSet`), paginação de 5 itens, ordenação estável.

| Rota | Filtros |
| --- | --- |
| `/api/stadium/` | `name`, `city` |
| `/api/match/` | `team` (nome, mandante ou visitante), `stage`, `status`, `team_group`, `stadium`, `kickoff_after`, `kickoff_before` |
| `/api/goal/` | `match`, `player`, `team` (time do jogador), `is_penalty`, `is_own_goal` |

Representação de `Match`: nomes das seleções e do estádio, lista de gols (jogador, minuto, acréscimo, pênalti, contra, time creditado) e `winner`. Escrita por ids.

Endpoints calculados:
- `GET /api/team-group/{id}/classificacao/` — lista ordenada de `{team, points, played, won, drawn, lost, goals_for, goals_against, goal_difference}` usando apenas partidas `FINISHED` com `stage == GROUP` daquele grupo. Ordem: pontos, saldo, gols pró, nome. Seleções sem jogos aparecem zeradas.
- `GET /api/player/artilheiros/` — `{player, team, goals, penalties}` ordenado por gols (desc) e nome; ignora gols contra e jogadores sem gols; filtro `team`; paginado.

A lógica fica em `core/services.py` (`group_standings(group)`, `top_scorers(queryset)`); as views só chamam.

## 3. Dados da Copa 2022

- Fonte: openfootball/worldcup.json (CC0), 64 partidas, 172 gols.
- Arquivo versionado: `data/worldcup2022.json`, gerado a partir da fonte e complementado com federações das 32 seleções, os 32 técnicos e capacidade dos 8 estádios.
- Comando `python manage.py seed_worldcup2022`: idempotente (`update_or_create` por chaves naturais), transacional. `--reset` apaga partidas, gols, estádios, jogadores, técnicos, seleções e grupos antes de carregar.
- Horários da fonte estão no fuso do Catar (UTC+3) e são gravados com timezone.

## 4. Documentação, configuração e deploy

- drf-spectacular: `/api/schema/` e Swagger em `/api/docs/`; `/` redireciona para `/api/docs/`.
- Configuração por variáveis de ambiente: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DATABASE_URL` (dj-database-url, default SQLite local), `CORS_ALLOWED_ORIGINS` (django-cors-headers).
- Produção: gunicorn, whitenoise para estáticos.
- `Dockerfile`: imagem slim, `collectstatic` no build; no start roda `migrate`, `seed_worldcup2022` e, se `DJANGO_SUPERUSER_USERNAME`/`DJANGO_SUPERUSER_PASSWORD` existirem, cria o superusuário.
- `render.yaml`: serviço web Docker no plano gratuito, SQLite efêmero (dados recarregados a cada deploy).
- GitHub Actions: roda `python manage.py test` em push e pull request; selo no README.

## 5. Testes

- Services: classificação (pontos, desempate por saldo e gols pró, só partidas encerradas de grupo), artilharia (ignora gol contra, conta pênaltis), `scoring_team` em gol contra, `winner` com pênaltis.
- Validações de `Match` e `Goal` (cada regra das tabelas acima).
- Endpoints novos: permissões, filtros, endpoints calculados.
- Seed: roda o comando e confere 64 partidas, 172 gols, gols batendo com o placar em todas as partidas, Mbappé com 8 gols no topo da artilharia, Argentina vencedora da final nos pênaltis (4–2), Brasil 1º do grupo G; rodar duas vezes não duplica.

## 6. README

Atualizar com: novos endpoints e filtros, link público, Swagger, Docker, deploy, comando de seed, selo do CI e limitações conhecidas.

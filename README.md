# Rumo ao Hexa API 🏆

[![Tests](https://github.com/LuisTapia08/rumo-ao-hexa-api/actions/workflows/tests.yml/badge.svg)](https://github.com/LuisTapia08/rumo-ao-hexa-api/actions/workflows/tests.yml)

🔗 Demo: _adicione o link após o deploy no Render_

API REST com os dados reais da **Copa do Mundo de 2022**: grupos, seleções, técnicos, estádios, partidas, gols, classificação dos grupos e artilharia. O objetivo é servir de backend para um front-end futuro que acompanhe a campanha do Brasil rumo ao hexa.

Feita com **Django**, **Django REST Framework**, autenticação **JWT**, filtros com **django-filter** e documentação interativa (Swagger) com **drf-spectacular**.

## Funcionalidades

- CRUD de grupos, seleções, jogadores, técnicos, estádios, partidas e gols
- Leitura pública; criação, edição e exclusão exigem autenticação (JWT)
- Dataset real da Copa de 2022: 64 partidas e 172 gols, carregados por um comando de seed
- Classificação de cada grupo calculada a partir dos jogos encerrados
- Ranking de artilheiros (Mbappé lidera com 8 gols)
- Validações de negócio nas partidas e nos gols (pênaltis só no mata-mata, jogador da seleção certa, etc.)
- Filtros por nome, faixas numéricas, datas e campos de escolha
- Paginação em todas as listagens
- Documentação Swagger em `/api/docs/`
- Painel administrativo do Django
- Docker, blueprint de deploy no Render e testes automatizados no GitHub Actions

## Tecnologias

| Pacote | Versão |
| --- | --- |
| Python | 3.12+ (a imagem Docker e o CI usam 3.14) |
| Django | 6.0 |
| Django REST Framework | 3.17 |
| djangorestframework-simplejwt | 5.5 |
| django-filter | 25.2 |
| drf-spectacular | 0.30 |
| gunicorn + whitenoise | servidor e arquivos estáticos em produção |
| Banco de dados | SQLite (ou outro via `DATABASE_URL`) |

## Como rodar localmente

```bash
# 1. Clone o repositório
git clone https://github.com/LuisTapia08/rumo-ao-hexa-api.git
cd rumo-ao-hexa-api

# 2. Crie e ative o ambiente virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/macOS

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Crie o banco, carregue os dados da Copa 2022 e crie um administrador
python manage.py migrate
python manage.py seed_worldcup2022
python manage.py createsuperuser

# 5. Suba o servidor
python manage.py runserver
```

A API fica disponível em `http://127.0.0.1:8000/api/`, a documentação Swagger em `http://127.0.0.1:8000/api/docs/` (a raiz `/` redireciona para ela) e o admin em `http://127.0.0.1:8000/admin/`.

### Seed dos dados da Copa 2022

```bash
python manage.py seed_worldcup2022           # carrega (ou atualiza) os dados
python manage.py seed_worldcup2022 --reset   # apaga os dados da Copa e recarrega do zero
```

O comando é **idempotente**: pode ser executado várias vezes sem duplicar registros. Rode `python manage.py migrate` antes dele. Ele carrega 8 grupos, 32 seleções com técnicos, 8 estádios, 64 partidas e 172 gols a partir de `data/worldcup2022.json`.

### Atalhos com Make

Se você tiver o `make` instalado, os comandos acima têm atalhos:

| Comando | O que faz |
| --- | --- |
| `make install` | Instala as dependências |
| `make migrations` | Gera novas migrações |
| `make migrate` | Aplica as migrações |
| `make user` | Cria um superusuário |
| `make run` | Sobe o servidor de desenvolvimento |
| `make test` | Roda os testes |

## Docker

```bash
docker build -t rumo-ao-hexa-api .
docker run --rm -p 8000:8000 \
  -e DJANGO_SUPERUSER_USERNAME=admin \
  -e DJANGO_SUPERUSER_PASSWORD=troque-esta-senha \
  rumo-ao-hexa-api
```

Ao iniciar, o contêiner aplica as migrações, roda o `seed_worldcup2022`, cria o superusuário (se `DJANGO_SUPERUSER_USERNAME` e `DJANGO_SUPERUSER_PASSWORD` forem informados e ele ainda não existir) e sobe o gunicorn na porta `8000` (ou em `$PORT`). Depois, acesse `http://127.0.0.1:8000/api/docs/`.

### Variáveis de ambiente

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `SECRET_KEY` | chave de desenvolvimento | Chave secreta do Django. **Defina em produção** |
| `DEBUG` | `True` | Use `False` em produção |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Hosts permitidos, separados por vírgula |
| `CSRF_TRUSTED_ORIGINS` | vazio | Origens confiáveis para CSRF (ex.: `https://*.onrender.com`) |
| `CORS_ALLOWED_ORIGINS` | vazio | Origens de front-ends autorizados a consumir a API |
| `DATABASE_URL` | SQLite local (`db.sqlite3`) | URL do banco (via `dj-database-url`) |
| `DJANGO_SUPERUSER_USERNAME` / `DJANGO_SUPERUSER_PASSWORD` / `DJANGO_SUPERUSER_EMAIL` | vazio | Criam o superusuário na inicialização do contêiner |

## Deploy no Render

O repositório já traz um `render.yaml` (serviço web Docker no plano gratuito).

1. No [Render](https://render.com), clique em **New → Blueprint**.
2. Conecte o repositório `LuisTapia08/rumo-ao-hexa-api` e escolha a branch.
3. Preencha as variáveis pedidas: `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_PASSWORD` e `DJANGO_SUPERUSER_EMAIL`.
4. Confirme com **Apply**. Quando o deploy terminar, abra a URL do serviço: ela redireciona para o Swagger.

> No plano gratuito o serviço "dorme" após cerca de 15 minutos sem acessos, e a primeira requisição depois disso leva de 30 a 50 segundos. O banco SQLite é efêmero: os dados são recarregados pelo seed a cada deploy ou reinício, e qualquer registro criado pela API é perdido.

## Modelo de dados

```
TeamGroup (grupo)  1 ──── N  Team (seleção)  1 ──── N  Player (jogador)  1 ──── N  Goal (gol)
                                             1 ──── N  Coach (técnico)

Stadium (estádio)  1 ──── N  Match (partida)  1 ──── N  Goal (gol)
Team (mandante e visitante) e TeamGroup (fase de grupos) também se ligam a Match
```

- **TeamGroup**: nome e descrição do grupo (ex.: "Grupo G").
- **Team**: nome, federação, ano de fundação (opcional) e grupo. Seleções sem grupo aparecem como "Fora da copa".
- **Player**: nome e seleção; dados físicos, posição, número da camisa e pé preferido são opcionais. O número é único dentro de cada seleção.
- **Coach**: nome, seleção e dados físicos opcionais.
- **Stadium**: nome (único), cidade e capacidade.
- **Match**: mandante, visitante, estádio, data/hora (`kickoff`), fase (`stage`), grupo, `status`, placar e pênaltis. A resposta traz os nomes das seleções e do estádio, a lista de gols e o `winner` (considerando os pênaltis).
- **Goal**: partida, jogador, minuto (1 a 120), acréscimos, pênalti e gol contra. A resposta traz `scoring_team`, a seleção que recebe o gol (o adversário, no gol contra).

Regras de validação (retornam `400`): partidas da fase de grupos exigem um grupo, e as duas seleções devem pertencer a ele; partida encerrada exige placar; pênaltis só valem no mata-mata, com placar empatado e sem terminar empatados; o jogador de um gol deve ser de uma das seleções da partida; um gol não pode ser pênalti e contra ao mesmo tempo.

Valores de `stage`: `GROUP`, `ROUND_OF_32`, `ROUND_OF_16`, `QUARTER_FINAL`, `SEMI_FINAL`, `THIRD_PLACE`, `FINAL`. Valores de `status`: `SCHEDULED`, `LIVE`, `FINISHED`.

Todos os registros têm `id`, `is_active`, `created_at` e `updated_at`.

## Autenticação

As requisições `GET` são públicas. Para `POST`, `PUT`, `PATCH` e `DELETE` é preciso enviar um token JWT.

**Obter o token:**

```bash
curl -X POST http://127.0.0.1:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "seu_usuario", "password": "sua_senha"}'
```

A resposta traz um `access` (vida curta) e um `refresh`. Envie o `access` no cabeçalho:

```bash
curl -X POST http://127.0.0.1:8000/api/team-group/ \
  -H "Authorization: Bearer SEU_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Grupo G", "description": "Grupo do Brasil", "is_active": true}'
```

**Renovar o token:** `POST /api/token/refresh/` com `{"refresh": "SEU_REFRESH_TOKEN"}`.

> No Swagger (`/api/docs/`), as rotas de leitura funcionam direto no navegador. Logado no admin, você também consegue escrever pela interface navegável do DRF.

## Endpoints

| Método | Rota | Descrição |
| --- | --- | --- |
| `GET` | `/api/docs/` | Documentação interativa (Swagger) |
| `GET` | `/api/schema/` | Schema OpenAPI |
| `POST` | `/api/token/` | Obtém o par de tokens JWT |
| `POST` | `/api/token/refresh/` | Renova o token de acesso |
| `GET` `POST` | `/api/team-group/` | Lista ou cria grupos |
| `GET` `PUT` `PATCH` `DELETE` | `/api/team-group/{id}/` | Detalha, edita ou remove um grupo |
| `GET` | `/api/team-group/{id}/classificacao/` | Tabela de classificação do grupo |
| `GET` `POST` | `/api/team/` | Lista ou cria seleções |
| `GET` `PUT` `PATCH` `DELETE` | `/api/team/{id}/` | Detalha, edita ou remove uma seleção |
| `GET` `POST` | `/api/player/` | Lista ou cria jogadores |
| `GET` `PUT` `PATCH` `DELETE` | `/api/player/{id}/` | Detalha, edita ou remove um jogador |
| `GET` | `/api/player/canhotos/` | Lista apenas os jogadores canhotos |
| `GET` | `/api/player/artilheiros/` | Ranking de artilheiros |
| `GET` `POST` | `/api/coach/` | Lista ou cria técnicos |
| `GET` `PUT` `PATCH` `DELETE` | `/api/coach/{id}/` | Detalha, edita ou remove um técnico |
| `GET` `POST` | `/api/stadium/` | Lista ou cria estádios |
| `GET` `PUT` `PATCH` `DELETE` | `/api/stadium/{id}/` | Detalha, edita ou remove um estádio |
| `GET` `POST` | `/api/match/` | Lista ou cria partidas |
| `GET` `PUT` `PATCH` `DELETE` | `/api/match/{id}/` | Detalha, edita ou remove uma partida |
| `GET` `POST` | `/api/goal/` | Lista ou cria gols |
| `GET` `PUT` `PATCH` `DELETE` | `/api/goal/{id}/` | Detalha, edita ou remove um gol |

### Exemplos

**Partidas do Brasil** (como mandante ou visitante):

```
GET /api/match/?team=Brasil
```

**Classificação de um grupo** (use o `id` do grupo em `/api/team-group/`). Cada item traz `team`, `team_id`, `points`, `played`, `won`, `drawn`, `lost`, `goals_for`, `goals_against` e `goal_difference`, ordenados por pontos, saldo de gols, gols pró e nome:

```
GET /api/team-group/{id}/classificacao/
```

```json
{
  "team": "Brasil",
  "team_id": 1,
  "points": 6,
  "played": 3,
  "won": 2,
  "drawn": 0,
  "lost": 1,
  "goals_for": 3,
  "goals_against": 1,
  "goal_difference": 2
}
```

_(Exemplo ilustrativo do formato; os valores reais vêm do banco.)_

**Artilheiros** (cada item traz `player`, `team`, `goals` e `penalties`; gols contra não contam):

```
GET /api/player/artilheiros/
GET /api/player/artilheiros/?team=Argentina
```

**Gols de pênalti da Argentina:**

```
GET /api/goal/?team=Argentina&is_penalty=true
```

**A final e as partidas a partir de uma data:**

```
GET /api/match/?stage=FINAL&status=FINISHED
GET /api/match/?kickoff_after=2022-12-01T00:00:00Z
```

> Os nomes das seleções estão em português (`Brasil`, `Argentina`, `Holanda`...). Consulte `/api/team/` para ver os nomes exatos.

### Paginação

As listagens retornam 5 itens por página. Use `?page=2`, `?page=3`, etc. A resposta tem o formato:

```json
{
  "count": 64,
  "next": "http://127.0.0.1:8000/api/match/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

### Filtros

Os filtros são passados como parâmetros na URL e podem ser combinados.

**Grupos, seleções, jogadores, técnicos e estádios:** `name` (busca parcial), `id`, `is_active`.

**Seleções (`/api/team/`)**

| Parâmetro | Exemplo |
| --- | --- |
| `federation` | `?federation=cbf` |
| `year_founded` | `?year_founded=1914` |
| `year_founded__gte` / `year_founded__lte` | `?year_founded__gte=1900&year_founded__lte=1950` |

**Jogadores e técnicos (`/api/player/` e `/api/coach/`)**

| Parâmetro | Exemplo |
| --- | --- |
| `birth_date_gt` / `birth_date_lt` | `?birth_date_gt=1995-01-01` |
| `height_min` / `height_max` | `?height_min=1.80` |
| `weight_min` / `weight_max` | `?weight_max=80` |
| `shirt_size` | `?shirt_size=M` (`XS`, `S`, `M`, `L`, `XL`) |

**Somente jogadores (`/api/player/`)**

| Parâmetro | Exemplo |
| --- | --- |
| `team` | `?team=Brasil` (nome exato da seleção) |
| `position` | `?position=FW` (`GK`, `DF`, `MF`, `FW`) |
| `foot_preference` | `?foot_preference=L` (`L`, `R`, `B`) |
| `foot_size_min` / `foot_size_max` | `?foot_size_min=40` |

**Somente técnicos (`/api/coach/`)**

| Parâmetro | Exemplo |
| --- | --- |
| `team__name` | `?team__name=bras` (busca parcial) |

**Estádios (`/api/stadium/`)**

| Parâmetro | Exemplo |
| --- | --- |
| `city` | `?city=lusail` (busca parcial) |

**Partidas (`/api/match/`)**

| Parâmetro | Exemplo |
| --- | --- |
| `team` | `?team=Brasil` (mandante ou visitante, sem distinguir caixa) |
| `stage` | `?stage=QUARTER_FINAL` |
| `status` | `?status=FINISHED` |
| `team_group` | `?team_group=7` (id do grupo) |
| `stadium` | `?stadium=3` (id do estádio) |
| `kickoff_after` / `kickoff_before` | `?kickoff_after=2022-12-01T00:00:00Z` |

**Gols (`/api/goal/`)**

| Parâmetro | Exemplo |
| --- | --- |
| `team` | `?team=Argentina` (seleção do jogador, sem distinguir caixa) |
| `match` | `?match=64` (id da partida) |
| `player` | `?player=10` (id do jogador) |
| `is_penalty` / `is_own_goal` | `?is_penalty=true` |

**Artilheiros (`/api/player/artilheiros/`)**: aceita `team` (nome da seleção, sem distinguir caixa).

**Exemplo combinado:** atacantes canhotos da Argentina.

```
GET /api/player/?team=Argentina&position=FW&foot_preference=L
```

## Testes

```bash
python manage.py test
```

Os testes cobrem permissões (leitura pública e escrita com JWT), filtros, paginação, as validações de partidas e gols, a classificação, a artilharia e o seed (64 partidas, 172 gols, Mbappé no topo da artilharia e a final vencida pela Argentina nos pênaltis). O GitHub Actions roda a suíte a cada push e pull request.

## Limitações conhecidas

- **Classificação:** o desempate usa apenas pontos, saldo de gols, gols pró e nome. Não há confronto direto nem fair play.
- **Jogadores:** só têm dados básicos (nome e seleção). Dados físicos, posição, número e pé preferido são opcionais e ficam vazios no dataset carregado, pois não há fonte confiável para eles.
- **Mata-mata:** a fase é apenas um atributo da partida; o chaveamento não é gerado automaticamente.
- **Banco no plano gratuito do Render:** o SQLite é efêmero e recarregado a cada deploy ou reinício.
- **`kickoff_before` / `kickoff_after`:** com apenas a data (ex.: `2022-12-18`), a comparação é feita contra a meia-noite desse dia.
- **Fuso horário:** os horários da fonte estão no fuso do Catar (UTC+3) e são gravados com timezone.

## Próximos passos

- [ ] Front-end para visualizar a campanha

## Créditos

- Dados da Copa de 2022: [openfootball/worldcup.json](https://github.com/openfootball/worldcup.json) (domínio público, CC0).
- A base do projeto nasceu em um curso da FPF Tech, a partir do repositório inicial do professor Abraão Brandão, e foi concluída por Luis Tapia.

## Autor

Feito por [Luis Tapia](https://github.com/LuisTapia08).

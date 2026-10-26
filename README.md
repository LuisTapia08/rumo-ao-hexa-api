# Rumo ao Hexa API 🏆

API REST para consultar dados da Copa do Mundo: grupos, seleções, jogadores e técnicos. O objetivo é servir de backend para um front-end futuro que acompanhe a campanha do Brasil rumo ao hexa.

Feita com **Django**, **Django REST Framework**, autenticação **JWT** e filtros com **django-filter**.

## Funcionalidades

- CRUD completo de grupos, seleções, jogadores e técnicos
- Leitura pública; criação, edição e exclusão exigem autenticação (JWT)
- Filtros por nome, faixas numéricas (altura, peso, ano de fundação), datas e campos de escolha
- Paginação em todas as listagens
- Endpoint dedicado para jogadores canhotos
- Painel administrativo do Django

## Tecnologias

| Pacote | Versão |
| --- | --- |
| Python | 3.12+ |
| Django | 6.0 |
| Django REST Framework | 3.17 |
| djangorestframework-simplejwt | 5.5 |
| django-filter | 25.2 |
| Banco de dados | SQLite |

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

# 4. Crie o banco e um usuário administrador
python manage.py migrate
python manage.py createsuperuser

# 5. Suba o servidor
python manage.py runserver
```

A API fica disponível em `http://127.0.0.1:8000/api/` e o admin em `http://127.0.0.1:8000/admin/`.

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

## Modelo de dados

```
TeamGroup (grupo)  1 ──── N  Team (seleção)  1 ──── N  Player (jogador)
                                             1 ──── N  Coach (técnico)
```

- **TeamGroup**: nome e descrição do grupo (ex.: "Grupo G").
- **Team**: nome, federação, ano de fundação e grupo. Seleções sem grupo aparecem como "Fora da copa".
- **Player**: dados físicos, posição, número da camisa, pé preferido e seleção. O número é único dentro de cada seleção.
- **Coach**: dados físicos e seleção.

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

> Logado no admin, você também consegue escrever pela interface navegável do DRF no próprio navegador.

## Endpoints

| Método | Rota | Descrição |
| --- | --- | --- |
| `POST` | `/api/token/` | Obtém o par de tokens JWT |
| `POST` | `/api/token/refresh/` | Renova o token de acesso |
| `GET` `POST` | `/api/team-group/` | Lista ou cria grupos |
| `GET` `PUT` `PATCH` `DELETE` | `/api/team-group/{id}/` | Detalha, edita ou remove um grupo |
| `GET` `POST` | `/api/team/` | Lista ou cria seleções |
| `GET` `PUT` `PATCH` `DELETE` | `/api/team/{id}/` | Detalha, edita ou remove uma seleção |
| `GET` `POST` | `/api/player/` | Lista ou cria jogadores |
| `GET` `PUT` `PATCH` `DELETE` | `/api/player/{id}/` | Detalha, edita ou remove um jogador |
| `GET` | `/api/player/canhotos/` | Lista apenas os jogadores canhotos |
| `GET` `POST` | `/api/coach/` | Lista ou cria técnicos |
| `GET` `PUT` `PATCH` `DELETE` | `/api/coach/{id}/` | Detalha, edita ou remove um técnico |

### Paginação

As listagens retornam 5 itens por página. Use `?page=2`, `?page=3`, etc. A resposta tem o formato:

```json
{
  "count": 21,
  "next": "http://127.0.0.1:8000/api/player/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

### Filtros

Os filtros são passados como parâmetros na URL e podem ser combinados.

**Todos os recursos:** `name` (busca parcial), `id`, `is_active`.

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

**Exemplo combinado:** atacantes canhotos do Brasil.

```
GET /api/player/?team=Brasil&position=FW&foot_preference=L
```

## Testes

```bash
python manage.py test
```

Os testes cobrem permissões (leitura pública e escrita com JWT), filtros, paginação e a regra de número único por seleção.

## Próximos passos

- [ ] Estádios e partidas (`Stadium` e `Match`), com fase, data e placar
- [ ] Gols por partida e ranking de artilheiros
- [ ] Tabela de classificação de cada grupo calculada a partir dos jogos
- [ ] Front-end para visualizar a campanha

## Autor

Feito por [Luis Tapia](https://github.com/LuisTapia08).

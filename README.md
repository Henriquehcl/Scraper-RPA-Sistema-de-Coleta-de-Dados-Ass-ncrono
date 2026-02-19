# Scraper RPA — Sistema de Coleta de Dados Assíncrono

Sistema de scraping web com arquitetura orientada a eventos.

---

## Arquitetura

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   FastAPI   │────▶│  RabbitMQ   │────▶│   Workers   │
│    (API)    │     │   (Queue)   │     │  (Crawlers) │
└─────────────┘     └─────────────┘     └─────────────┘
       │                                       │
       │            ┌─────────────┐            │
       └───────────▶│  PostgreSQL │◀───────────┘
                    │    (Data)   │
                    └─────────────┘
```

**Fluxo assíncrono:**
1. `POST /crawl/*` cria um job no banco com status `pending` e publica mensagem no RabbitMQ
2. O Worker consome a mensagem da fila e executa o crawler correspondente
3. O crawler coleta os dados e os persiste no PostgreSQL
4. `GET /jobs/{job_id}` permite acompanhar o status em tempo real

---

## Stack Tecnológica

| Tecnologia | Versão | Uso |
|---|---|---|
| **Python** | 3.12 | Linguagem principal |
| **FastAPI** | 0.115+ | Framework web assíncrono |
| **Pydantic v2** | 2.9+ | Validação e serialização de dados |
| **SQLAlchemy** | 2.0+ | ORM assíncrono (asyncpg) |
| **PostgreSQL** | 15 | Banco de dados relacional |
| **RabbitMQ** | 3.12 | Broker de mensagens (filas) |
| **aio-pika** | 9.4+ | Cliente AMQP assíncrono |
| **Selenium** | 4.26+ | Scraping de páginas dinâmicas (Oscar) |
| **BeautifulSoup4** | 4.12+ | Parsing de HTML (Hockey) |
| **Docker + Compose** | latest | Containerização |
| **GitHub Actions** | — | CI/CD com push para GCR |

---

## Estrutura do Projeto

```
.
├── app/
│   ├── main.py                  # Ponto de entrada FastAPI (startup/shutdown)
│   ├── api/
│   │   └── routes/
│   │       ├── crawl.py         # POST /crawl/* — agendar coletas
│   │       ├── jobs.py          # GET /jobs, GET /jobs/{id}
│   │       └── results.py       # GET /results/*, GET /jobs/{id}/results
│   ├── core/
│   │   ├── config.py            # Settings via variáveis de ambiente (Pydantic)
│   │   └── database.py          # Engine/sessão SQLAlchemy async
│   ├── models/
│   │   ├── job.py               # Model: Job (status, tipo, timestamps)
│   │   ├── hockey.py            # Model: HockeyTeam
│   │   └── oscar.py             # Model: OscarFilm
│   ├── schemas/
│   │   ├── job.py               # Enums JobType, JobStatus + schemas Pydantic
│   │   ├── hockey.py            # Schemas de Hockey
│   │   └── oscar.py             # Schemas do Oscar
│   ├── services/
│   │   ├── job_service.py       # CRUD de jobs + consulta de resultados
│   │   └── queue_service.py     # Publisher/Consumer RabbitMQ (aio-pika)
│   └── crawlers/
│       ├── base.py              # BaseCrawler (ABC)
│       ├── hockey_crawler.py    # Scraping HTML + paginação (requests/BS4)
│       └── oscar_crawler.py     # Scraping AJAX + Selenium
├── worker/
│   └── main.py                  # Processo Worker: consome fila e executa crawlers
├── tests/
│   ├── conftest.py              # Fixtures globais
│   ├── unit/
│   │   ├── test_hockey_parser.py
│   │   ├── test_oscar_parser.py
│   │   └── test_job_service.py
│   └── integration/
│       ├── conftest.py          # Fixtures Testcontainers (PG + RabbitMQ)
│       ├── test_api_crawl.py
│       ├── test_api_jobs.py
│       └── test_api_results.py
├── .github/
│   └── workflows/
│       └── ci.yml               # Pipeline CI/CD (lint → unit → integration → build → push GCR)
├── Dockerfile                   # Imagem da API
├── Dockerfile.worker            # Imagem do Worker (inclui Chrome/ChromeDriver)
├── docker-compose.yml           # Orquestra API + Worker + PostgreSQL + RabbitMQ
├── requirements.txt             # Dependências de produção
├── requirements-dev.txt         # Dependências de desenvolvimento e testes
├── pyproject.toml               # Configuração de ruff, black, pytest, mypy
├── flake.nix                    # Ambiente Nix reproducível
└── .envrc                       # Configuração do direnv
```

---

## Como Executar

### Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) e [Docker Compose](https://docs.docker.com/compose/install/) instalados
- Git

### 1. Clonar o repositório

```bash
git clone <url-do-repositorio>
cd scraper-rpa
```

### 2. Configurar variáveis de ambiente (opcional)

```bash
cp .env.example .env
# Edite .env se quiser customizar credenciais
```

### 3. Subir todos os serviços

```bash
docker-compose up --build
```

Isso sobe:
- **API** em `http://localhost:8000`
- **PostgreSQL** em `localhost:5432`
- **RabbitMQ** em `localhost:5672` (Management UI: `http://localhost:15672`)
- **Worker** em background (consome a fila automaticamente)

### 4. Acessar a documentação interativa

Abra no browser: `http://localhost:8000/docs`

---

## Endpoints da API

### Agendar Coletas

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/crawl/hockey` | Agenda coleta dos times de hockey |
| `POST` | `/crawl/oscar` | Agenda coleta dos filmes do Oscar |
| `POST` | `/crawl/all` | Agenda ambas as coletas |

**Resposta (HTTP 202):**
```json
{
  "job_id": "uuid-do-job",
  "status": "pending",
  "message": "Job de coleta 'hockey' agendado com sucesso."
}
```

### Gerenciar Jobs

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/jobs` | Lista todos os jobs |
| `GET` | `/jobs/{job_id}` | Status e detalhes de um job |

**Status possíveis:** `pending` → `running` → `completed` / `failed`

### Consultar Resultados

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/jobs/{job_id}/results` | Dados coletados por um job específico |
| `GET` | `/results/hockey` | Todos os times de hockey coletados |
| `GET` | `/results/oscar` | Todos os filmes do Oscar coletados |

---

## Exemplo de Uso (curl)

```bash
# 1. Agendar coleta de hockey
curl -X POST http://localhost:8000/crawl/hockey

# 2. Verificar status do job (use o job_id retornado acima)
curl http://localhost:8000/jobs/<job_id>

# 3. Consultar resultados quando status = completed
curl http://localhost:8000/jobs/<job_id>/results

# 4. Listar todos os dados de hockey coletados
curl http://localhost:8000/results/hockey
```

---

## Fontes de Dados

### Hockey Teams

- **URL:** https://www.scrapethissite.com/pages/forms/
- **Estratégia:** `requests` + `BeautifulSoup4` — página HTML com paginação tradicional
- **Dados coletados:** Team Name, Year, Wins, Losses, OT Losses, Win%, GF, GA, Goal Diff

### Oscar Winning Films

- **URL:** https://www.scrapethissite.com/pages/ajax-javascript/
- **Estratégia:** `Selenium` (Chrome headless) — dados carregados via JavaScript/AJAX
- **Dados coletados:** Year, Title, Nominations, Awards, Best Picture

---

## Desenvolvimento Local

### Com Nix + direnv (Linux/macOS — recomendado)

```bash
# 1. Instalar Nix (se não tiver)
sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --daemon

# 2. Habilitar Flakes — adicionar ao ~/.config/nix/nix.conf:
# experimental-features = nix-command flakes

# 3. Instalar direnv e adicionar ao shell (~/.bashrc ou ~/.zshrc):
# eval "$(direnv hook bash)"

# 4. Ativar o ambiente
direnv allow
# O shell hook instala todas as dependências automaticamente
```

### Com virtualenv (qualquer OS)

```bash
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

pip install -r requirements-dev.txt
```

### Subir dependências localmente (sem Docker)

```bash
# PostgreSQL e RabbitMQ via Docker (só os serviços de infra)
docker-compose up postgres rabbitmq

# Rodar API localmente
uvicorn app.main:app --reload

# Rodar Worker localmente (outro terminal)
python -m worker.main
```

---

## Testes

### Testes Unitários

Testam parsers, lógica de negócio e validações sem dependências externas:

```bash
pytest tests/unit/ -v
```

### Testes de Integração

Usam **Testcontainers** para subir PostgreSQL e RabbitMQ reais em Docker:

```bash
pytest tests/integration/ -v
```

> **Requisito:** Docker em execução na máquina

### Todos os testes com cobertura

```bash
pytest --cov=app --cov-report=html
# Relatório em htmlcov/index.html
```

---

## Qualidade de Código

```bash
# Lint
ruff check .

# Formatação
black .

# Verificar formatação sem modificar
black --check .

# Type checking
mypy app/
```

---

## CI/CD — GitHub Actions

O pipeline (`.github/workflows/ci.yml`) executa em cada push/PR:

```
1. Lint        → ruff check + black --check
2. Unit Tests  → pytest tests/unit/
3. Integration → pytest tests/integration/ (Testcontainers)
4. Build       → docker build (API + Worker)
5. Push GCR    → push para Google Container Registry (somente em main)
```

### Configurar Push para GCR

Adicione os seguintes **Secrets** no repositório GitHub (`Settings > Secrets`):

| Secret | Descrição |
|--------|-----------|
| `GCP_PROJECT_ID` | ID do projeto no Google Cloud |
| `GCP_SA_KEY` | JSON da Service Account com permissão `roles/storage.admin` |

---

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `POSTGRES_HOST` | `localhost` | Host do PostgreSQL |
| `POSTGRES_PORT` | `5432` | Porta do PostgreSQL |
| `POSTGRES_USER` | `postgres` | Usuário do banco |
| `POSTGRES_PASSWORD` | `postgres` | Senha do banco |
| `POSTGRES_DB` | `scraper_db` | Nome do banco |
| `RABBITMQ_HOST` | `localhost` | Host do RabbitMQ |
| `RABBITMQ_PORT` | `5672` | Porta AMQP do RabbitMQ |
| `RABBITMQ_USER` | `guest` | Usuário do RabbitMQ |
| `RABBITMQ_PASSWORD` | `guest` | Senha do RabbitMQ |
| `SELENIUM_HEADLESS` | `true` | Chrome em modo headless |
| `SELENIUM_TIMEOUT` | `30` | Timeout do Selenium (segundos) |
| `DEBUG` | `false` | Ativa logs de debug e SQL |

---

## Decisões de Arquitetura

### Por que dois Dockerfiles?

A API e o Worker têm necessidades diferentes. A imagem do Worker inclui Chrome e ChromeDriver (para Selenium), o que aumenta significativamente o tamanho. Separar as imagens mantém a API leve e o Worker com tudo que precisa.

### Por que asyncpg + SQLAlchemy async?

FastAPI é async-first. Usar asyncpg com SQLAlchemy assíncrono evita bloqueios no event loop durante operações de banco, maximizando a throughput da API.

### Por que aio-pika?

É o cliente AMQP nativo para asyncio, desenvolvido pela equipe do aiohttp. Suporta reconexão automática (`connect_robust`) e prefetch para controle de carga no worker.

### Por que Testcontainers?

Permite testes de integração reais contra PostgreSQL e RabbitMQ sem dependência de infraestrutura fixa. Os containers sobem e descem automaticamente durante a execução dos testes, garantindo isolamento e reprodutibilidade.

---

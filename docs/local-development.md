# Desenvolvimento local

P1-01 entrega a base executável. A página inicial verifica API e banco e permite repetir a consulta. Não há login, CRUD, migrations, matching ou uso de IA nesta entrega.

## Pré-requisitos e estrutura

Para executar tudo: Docker Desktop com containers Linux e Docker Compose com suporte a `--wait`; Python 3.13+ para os scripts auxiliares. Para desenvolver fora dos containers: uv 0.12.7 e Node 24 com npm. A API usa Python 3.13, instalado por `uv python install 3.13` quando necessário.

```text
apps/api/                   FastAPI, psycopg, configuração e testes
  src/jobhunter_api/         pacote Python
  uv.lock                   dependências Python resolvidas
apps/web/                   React, TypeScript, Vite, Vitest
  package-lock.json         dependências npm resolvidas
compose.yaml                PostgreSQL + API + frontend
scripts/init_env.py          criação idempotente de credencial local
scripts/smoke_local.py       integração HTTP e recuperação opcional do banco
.github/workflows/ci.yml     lint, tipos, testes, builds, Compose e contratos
```

## Inicialização

Na raiz do projeto:

```powershell
python scripts/init_env.py
docker compose config --quiet
docker compose up --build --detach --wait --wait-timeout 120
python scripts/smoke_local.py
```

O primeiro build baixa imagens e dependências. O script cria `.env` com senha aleatória, sem imprimi-la. Se o arquivo já existir, preserva-o; uma senha vazia faz o Compose recusar a inicialização. Não publique `.env` ou a saída expandida de `docker compose config`.

| Serviço | Endereço padrão | Verificação |
|---|---|---|
| Web | http://127.0.0.1:5173 | `/healthz` verifica Nginx; a interface consulta a API |
| API via web | http://127.0.0.1:5173/api/docs | Swagger/OpenAPI |
| API direta | http://127.0.0.1:8000 | `/api/health/live` e `/api/health/ready` |
| PostgreSQL | `127.0.0.1:5433` | `pg_isready` e `SELECT 1` na readiness da API |

Todas as portas publicadas usam loopback. `.env` permite alterar `WEB_PORT`, `API_PORT` e `JOBHUNTER_DB_PORT` se estiverem ocupadas. O Compose mantém portas e DNS internos separados dos valores do host. Se alterar portas, passe `--web-url` e `--api-url` ao smoke.

Swagger usa os assets CDN padrão do FastAPI e pode precisar de acesso à internet; o frontend principal serve JavaScript/CSS locais. A política CSP estrita da página inicial não é aplicada ao Swagger.

```powershell
docker compose ps
docker compose logs --tail 80 api web
docker compose down
```

`down` preserva o volume `postgres_data`. Ao voltar, execute o comando `up` acima. Não use `down --volumes` para uma parada normal: ele elimina o banco. A senha inicial é persistida pelo PostgreSQL; editar `.env` após criar o volume não altera automaticamente a senha do banco. API e web executam sem root e com filesystem somente leitura, exceto `/tmp`.

## Desenvolvimento com recarga automática

Pare a API e a web do Compose antes de usar as mesmas portas no host:

```powershell
docker compose stop api web
docker compose up --detach db
uv python install 3.13
uv sync --project apps/api --locked
uv run --project apps/api --env-file .env uvicorn jobhunter_api.main:app --reload --host 127.0.0.1 --port 8000
```

Em outro terminal:

```powershell
cd apps/web
npm ci
npm run dev
```

O Vite usa `127.0.0.1:5173` e encaminha `/api` para `http://127.0.0.1:8000`. Se mudar a porta da API, ajuste `API_PROXY_TARGET` no ambiente do terminal e o argumento `--port`. O comando de recarga acima carrega `.env`; não inclua a senha na linha de comando. Para voltar ao Compose, encerre ambos os processos e execute `docker compose up --detach --wait` na raiz.

## Checks

API, dentro de `apps/api`:

```powershell
uv sync --locked
uv run --locked ruff check . ../../scripts/init_env.py ../../scripts/smoke_local.py
uv run --locked ruff format --check . ../../scripts/init_env.py ../../scripts/smoke_local.py
uv run --locked mypy
uv run --locked pytest
uv build
```

Frontend, dentro de `apps/web`:

```powershell
npm ci
npm run lint
npm run typecheck
npm test
npm run build
```

Integração com o Compose iniciado, na raiz:

```powershell
python scripts/smoke_local.py
python scripts/smoke_local.py --exercise-db-recovery
```

A segunda execução interrompe brevemente **somente o serviço `db` deste projeto**, verifica liveness 200/readiness 503 e reinicia o banco em um bloco `finally`. Aguarda readiness 200 sem reiniciar API/web; preserva os dados. Use quando uma interrupção local for aceitável.

Os mesmos checks estão no workflow de GitHub Actions, com jobs separados para API, web, integração Compose e contratos da fase 0. O job de integração elimina apenas seu volume descartável no runner. Não usa `.private/`, credenciais externas, AWS ou inferência paga. O workflow foi preparado localmente; não há execução remota enquanto este repositório não for hospedado no GitHub.

## Dados e próximos módulos

Os contextos de build são limitados a `apps/api` e `apps/web`, com `.dockerignore` por lista permitida. `.private/`, `.env`, ambientes virtuais e dependências instaladas são ignorados pelo Git. Não há montagem ou cópia do CV para os containers. O PostgreSQL ainda não contém tabelas de domínio. Autenticação é P1-02; perfil, migrations e seed fictício são P1-03.

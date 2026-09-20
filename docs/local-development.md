# Desenvolvimento local — P1 e P2

O núcleo inclui login, perfil factual, evidências, revisão de vagas, matching determinístico,
Inbox, tracker manual e exportação. P2 adiciona IA por chamada explícita e busca semântica.
Veja [configuração, privacidade, custos e benchmark de P2](phase-2/operations.md).
AWS e canais de envio continuam fora do runtime atual.

## Pré-requisitos

Docker Desktop com containers Linux e Compose com `--wait`; Python e uv 0.12.7. Para desenvolver o frontend/testar E2E: Node 24 e npm. A API usa Python 3.13; `uv sync` instala a versão selecionada quando necessário.

## Iniciar

Na raiz:

```powershell
python scripts/init_env.py
docker compose config --quiet
docker compose up --build --detach --wait --wait-timeout 120
uv sync --project apps/api --locked
uv run --project apps/api --env-file .env python -m jobhunter_api.manage bootstrap
python scripts/smoke_local.py
```

Abra http://127.0.0.1:5173. Entre como `local`, usando a senha de `.private/local-login.txt`. O bootstrap preserva a conta existente. `.env` contém duas credenciais distintas para administração e runtime; o inicializador preserva valores existentes e acrescenta a credencial runtime em uma instalação antiga. Não imprima nem publique `.env`.

O Compose inicia PostgreSQL, executa migrations/grants no serviço efêmero `migrate` e inicia API/web após os healthchecks. `migrate` terminar com código 0 é esperado. API e web executam sem root, com filesystem somente leitura e `/tmp` temporário. O runtime não recebe a senha administrativa no Compose.

| Serviço | Endereço padrão |
|---|---|
| Aplicação | http://127.0.0.1:5173 |
| Documentação da API | http://127.0.0.1:5173/api/docs |
| API direta | http://127.0.0.1:8000 |
| PostgreSQL | `127.0.0.1:5433` |

Todas as portas são loopback. `WEB_PORT`, `API_PORT` e `JOBHUNTER_DB_PORT` em `.env` permitem trocar portas ocupadas. O Compose ajusta as origens permitidas à porta web. O Swagger usa assets CDN padrão; a aplicação usa assets locais.

```powershell
docker compose ps
docker compose logs --tail 80 api web migrate
docker compose down
```

`down` preserva o banco. **Não use `down --volumes` em uma parada normal**, pois elimina os dados. Editar senhas em `.env` não altera automaticamente as senhas já persistidas no PostgreSQL.

## Primeiro fluxo

1. Em Perfil e evidências, registre uma evidência e confirme sua revisão.
2. Registre um fato com evidência, uso `matching` e revisão explícita; publique a versão do perfil.
3. Importe o texto de uma vaga; confirme seus campos e requisitos.
4. Avalie os requisitos com justificativas e fatos válidos. Observe score e cobertura juntos.
5. Abra as evidências do resultado; adicione à shortlist e acompanhe em Candidaturas.
6. Registre uma submissão somente se você já a realizou fora da aplicação, com data/canal/comprovante.

Alternativamente, o comando abaixo cria um **perfil fictício**, recusando um perfil que já tenha fatos. Não o use para misturar dados fictícios com o seu perfil real:

```powershell
uv run --project apps/api --env-file .env python -m jobhunter_api.manage seed
```

O CV e os fatos privados da fase 0 não foram importados automaticamente. [Contratos e decisões de runtime](phase-1/runtime-contracts.md).

## Recarga automática

```powershell
docker compose stop api web
docker compose up --detach --wait db
uv run --project apps/api --env-file .env python -m jobhunter_api.manage provision
uv run --project apps/api --env-file .env uvicorn jobhunter_api.main:app --reload --host 127.0.0.1 --port 8000 --no-access-log
```

Em outro terminal:

```powershell
cd apps/web
npm ci
npm run dev
```

O Vite usa porta 5173 e proxy `/api` para 8000. Se alterar a porta da API, configure `API_PROXY_TARGET` no terminal do Vite. Se alterar a porta do Vite, defina `JOBHUNTER_ALLOWED_ORIGINS` como lista JSON no ambiente da API. Nunca passe senha como argumento de linha de comando.

## Testes e checks

API, dentro de `apps/api`, com PostgreSQL iniciado:

```powershell
uv sync --locked
uv run --locked ruff check . ../../scripts/init_env.py ../../scripts/smoke_local.py ../../scripts/evaluate_phase1.py
uv run --locked ruff format --check . ../../scripts/init_env.py ../../scripts/smoke_local.py ../../scripts/evaluate_phase1.py
uv run --locked mypy
$env:JOBHUNTER_TEST_DB_NAME='jobhunter_test'
uv run --locked --env-file ../../.env pytest
uv run --locked python ../../scripts/evaluate_phase1.py --check
uv build
```

No shell POSIX, use `export JOBHUNTER_TEST_DB_NAME=jobhunter_test` no lugar da atribuição PowerShell. Testes integram com um banco separado e recusam nomes sem prefixo `jobhunter_test`. Sem a variável, os testes PostgreSQL são marcados como skipped; isso não conta como validação completa. Dois avisos de depreciação do cliente Starlette/httpx e AnyIO permanecem visíveis.

Frontend, dentro de `apps/web`:

```powershell
npm ci
npm run lint
npm run format:check
npm run typecheck
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

O E2E cria somente `jobhunter_test_e2e`, usa credenciais fictícias e servidores temporários nas portas 5174/8001. Não reutiliza a aplicação pessoal. Percorre perfil → importação → revisão → matching → evidência → tracker → exportação em desktop e mobile. No Windows, se o download do Chromium estiver indisponível e o Edge já estiver instalado:

```powershell
$env:PLAYWRIGHT_CHANNEL='msedge'
npm run test:e2e
```

Screenshots/traces ficam em `apps/web/test-results/` e o relatório em `apps/web/playwright-report/`, ignorados pelo Git. O frontend usa Prettier (`npm run format`), ESLint e TypeScript estrito.

Na raiz, com Compose iniciado:

```powershell
python scripts/smoke_local.py
python scripts/smoke_local.py --exercise-db-recovery
```

O segundo comando interrompe brevemente o `db` deste projeto, verifica liveness 200/readiness 503 e o reinicia em `finally`, sem apagar dados. `--web-url`/`--api-url` permitem portas diferentes. Os cinco jobs de CI cobrem API, frontend, Compose, browser E2E e contratos de design. O workflow está preparado; não foi executado no GitHub sem remote configurado.

## Privacidade

Exporte pela tela Privacidade. A eliminação completa dos dados da aplicação é um comando administrativo com confirmação explícita; veja [segurança e dados](phase-1/security-and-data.md). Não há endpoint de envio, coleta remota ou montagem de `.private/` nos containers. Backups/exportações privados não devem entrar no Git.

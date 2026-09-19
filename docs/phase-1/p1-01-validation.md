# P1-01 — Estrutura e ambiente local

Estado: implementado e verificado localmente em 2026-09-19. A fase 1 continua com P1-02.

| Critério | Implementação / evidência |
|---|---|
| Monorepo e arquitetura | `apps/api` e `apps/web`; ADR-001 atualizado; sem módulos vazios para funções futuras |
| Compose com healthchecks | PostgreSQL, API e Nginx iniciados e saudáveis; API readiness executa `SELECT 1` |
| Configuração sem segredos no código | `.env.example` com senha vazia; inicializador cria senha aleatória sem sobrescrever `.env` |
| Versões e lockfiles | Python 3.13, Node 24; `uv.lock`, `package-lock.json`; imagens por digest e ações de CI por SHA |
| Lint, tipos, testes, builds | Ruff, mypy, pytest; ESLint, TypeScript, Vitest; wheel/sdist da API e build Vite |
| CI | Workflow com quatro jobs; comandos executados localmente, execução no GitHub ainda não realizada |
| Portas locais | Publicação em `127.0.0.1` nas portas padrão 5173, 8000 e 5433 |
| Dados privados | `.private/` e `.env` ignorados pelo Git; builds por lista permitida e contextos restritos |

## Verificações executadas

- API: 6 testes aprovados, cobrindo liveness independente do banco, readiness 200/503, redaction de credenciais e configuração inválida. Ruff/format e mypy aprovados; wheel/sdist gerados.
- Web: 4 testes aprovados, cobrindo sucesso, erro HTTP com nova tentativa, resposta inválida e falha de rede. ESLint, TypeScript e build de produção aprovados. Instalação npm não reportou vulnerabilidades naquele momento.
- Compose: build das duas imagens e três serviços saudáveis. Smoke verifica frontend, assets, API direta e pelo proxy, OpenAPI e Swagger. Banco interrompido e recuperado com liveness 200, readiness 503 durante indisponibilidade e retorno a 200 sem reiniciar API/web.
- Contratos públicos da fase 0: validador aprovado, incluindo 15 casos de rejeição e os 20 casos reais derivados. Isso não executa o futuro algoritmo de matching.
- Git inicializado localmente; `.env`, `.private/` e dependências locais confirmados como ignorados. Sem commit, remote ou publicação.

## Limites da validação

O navegador de automação não estava disponível; não houve inspeção visual nem teste E2E em navegador real. Foram executados testes de componentes em jsdom e smoke HTTP contra os containers reais. O workflow não foi executado no GitHub, pois não existe remote configurado.

Pytest emite dois avisos de depreciação das dependências de teste Starlette/httpx e AnyIO; os testes passam e os avisos permanecem visíveis. Revisar essas dependências ao atualizar o lockfile.

Não há autenticação, dados privados na aplicação, tabelas de domínio, migrations, integração com IA, recursos AWS ou envio de candidaturas. Esses recursos têm itens próprios no backlog.

Operação e comandos reproduzíveis: [desenvolvimento local](../local-development.md).

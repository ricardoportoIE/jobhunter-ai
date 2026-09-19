# Implementação da fase 1

Cada etapa tem commit local próprio. Sem publicação remota.

| Etapa | Resultado | Validação |
|---|---|---|
| P1-01 | Compose, API, web e lockfiles | 10 testes, builds e smoke com recuperação do banco |
| P1-02 | Conta local, Argon2, sessão opaca de 8h, logout, CSRF, origem e limite persistente de login | 11 testes API com PostgreSQL isolado; hash, expiração, replay, 401/403/429 |
| P1-03 | CRUD de perfil/fatos/evidências, revisão e snapshots, validade/usos, versão otimista e seed fictício opcional | Integração: review obrigatório, snapshot preservado, revogação invalida perfil, 409 e isolamento por proprietário |
| P1-04 | Importação de texto com SHA-256, referência sem fetch, requisitos manuais e confirmação antes de PARSED | Integração: texto preservado, desconhecidos null, filtros, limites 50.000 caracteres/128 KiB, payload XSS armazenado como texto |
| P1-05 | Identidade por fonte+ID, URL canônica e hash+localidade; idempotência vinculada ao ator e payload | Repetição, conflito 409, importações concorrentes e texto igual em cidades diferentes; duplicata nunca sobrescreve vaga revisada |
| P1-06 | Matching determinístico v0.2, score/cobertura separados, fatos válidos e snapshots reproduzíveis | Exemplo ADR 68/0,50; half-up; pesos; blockers; autorização futura desconhecida; fatos revogados/vencidos e análise obsoleta |
| P1-07 | Login, perfil, fatos/evidências, Inbox com filtros/paginação, importação, revisão, avaliação e detalhe com fontes | TypeScript/ESLint/build; componentes com falha/retry/vazio, XSS como texto, versão otimista, score/cobertura juntos e alerta de análise obsoleta |
| P1-08 | Shortlist única por vaga, tracker com linha do tempo e transições autorizadas; envio somente como registro manual confirmado | Integração: duplicata, replay de evento, conflito de payload, estados terminais, data futura e confirmação/comprovante obrigatórios |
| P1-09 | Papel runtime separado, auditoria e snapshots append-only, exportação privada e eliminação administrativa explícita | SQL UPDATE/DELETE/TRUNCATE negado; falha de auditoria reverte escrita; respostas/logs sem payload; export sem credenciais e erasure revoga sessões |
| P1-10 | E2E fictício desktop/mobile, avaliação pública reproduzível, cinco jobs de CI e documentação operacional | 36 testes API + 9 componentes + 2 E2E; lint/tipos/builds; Compose do zero e smoke; revisão humana das divergências pendente |

## Fechamento técnico — 2026-09-20

Os 47 testes passaram localmente. O E2E usa Edge 153 em sessão headless isolada, pois o download do Chromium do Playwright expirou nesta rede. Testou navegação por teclado, fluxo completo, exportação, logout, XSS como texto e ausência de rolagem horizontal no mobile. As capturas desktop/mobile foram inspecionadas. [Relatório final](validation.md).

Os cinco jobs de CI estão definidos e o YAML passou na validação de schema; não houve execução no GitHub nem push. O dataset público teve 20/20 invariantes conservadores preservados, 12/20 recomendações mapeadas coincidentes e diferenças em 18 casos. A confirmação humana não foi presumida: [resultados e limites](evaluation-results.md).

## Commits locais

| Etapa | Commit |
|---|---|
| P1-01 | `bbfa9df` |
| P1-02 | `6e541cc` |
| P1-03 | `7c73e0a` |
| P1-04 | `276525a` |
| P1-05 | `efe9f46` |
| P1-06 | `4874289` |
| P1-07 | `d1a8ab4` |
| P1-08 | `59751fa` |
| P1-09 | `e1d9ca6` |
| P1-10 | commit que adiciona este fechamento; localizar por `git log --grep=P1-10` |

Credenciais iniciais são geradas por `uv run --project apps/api --env-file .env python -m jobhunter_api.manage bootstrap` e guardadas em `.private/local-login.txt`, nunca no Git. O comando não redefine uma conta existente. Migrations têm checksum e lock transacional. Testes de integração exigem `JOBHUNTER_TEST_DB_NAME` começando por `jobhunter_test`, separado do banco da aplicação.

Referências de implementação: [transações psycopg](https://www.psycopg.org/psycopg3/docs/basic/transactions.html), [Argon2](https://argon2-cffi.readthedocs.io/en/stable/howto.html), [privilégios PostgreSQL](https://www.postgresql.org/docs/17/ddl-priv.html).

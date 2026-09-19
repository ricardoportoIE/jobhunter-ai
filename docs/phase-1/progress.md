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

Credenciais iniciais são geradas por `uv run --project apps/api --env-file .env python -m jobhunter_api.manage bootstrap` e guardadas em `.private/local-login.txt`, nunca no Git. O comando não redefine uma conta existente. Migrations têm checksum e lock transacional. Testes de integração exigem `JOBHUNTER_TEST_DB_NAME` começando por `jobhunter_test`, separado do banco da aplicação.

Referências de implementação: [transações psycopg](https://www.psycopg.org/psycopg3/docs/basic/transactions.html), [Argon2](https://argon2-cffi.readthedocs.io/en/stable/howto.html), [privilégios PostgreSQL](https://www.postgresql.org/docs/17/ddl-priv.html).

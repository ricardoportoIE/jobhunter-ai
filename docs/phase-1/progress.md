# Implementação da fase 1

Cada etapa tem commit local próprio. Sem publicação remota.

| Etapa | Resultado | Validação |
|---|---|---|
| P1-01 | Compose, API, web e lockfiles | 10 testes, builds e smoke com recuperação do banco |
| P1-02 | Conta local, Argon2, sessão opaca de 8h, logout, CSRF, origem e limite persistente de login | 11 testes API com PostgreSQL isolado; hash, expiração, replay, 401/403/429 |

Credenciais iniciais são geradas por `uv run --project apps/api --env-file .env python -m jobhunter_api.manage bootstrap` e guardadas em `.private/local-login.txt`, nunca no Git. O comando não redefine uma conta existente. Migrations têm checksum e lock transacional. Testes de integração exigem `JOBHUNTER_TEST_DB_NAME` começando por `jobhunter_test`, separado do banco da aplicação.

Referências de implementação: [transações psycopg](https://www.psycopg.org/psycopg3/docs/basic/transactions.html), [Argon2](https://argon2-cffi.readthedocs.io/en/stable/howto.html), [privilégios PostgreSQL](https://www.postgresql.org/docs/17/ddl-priv.html).

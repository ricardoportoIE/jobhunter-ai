# Segurança e dados da fase 1

O runtime utiliza `jobhunter_app`, sem superuser, CREATE DATABASE, CREATE ROLE ou CREATE no schema. O serviço efêmero `migrate` utiliza a credencial administrativa apenas para migrations e grants e termina antes da API iniciar. A API recebe somente a credencial runtime no Compose. Fora do Docker, `Settings.runtime()` seleciona `JOBHUNTER_APP_DB_PASSWORD` de `.env`.

Auditoria e snapshots permitem SELECT/INSERT ao runtime; UPDATE, DELETE, TRUNCATE e DDL são negados. Isso protege contra a aplicação, não contra o administrador do PostgreSQL. Cada mutação e seu evento são gravados na mesma transação. Escritas são serializadas por proprietário com advisory lock e versões otimistas; o índice de candidatura impede duplicatas também no banco.

Sessões usam tokens opacos aleatórios com hash no banco, cookie HttpOnly/SameSite Strict, expiração absoluta de oito horas, logout com revogação e CSRF + origem permitida nas escritas. HTTP local usa cookie sem Secure; um futuro deploy HTTPS deve habilitar `JOBHUNTER_COOKIE_SECURE=true` e definir origens explícitas. Não há acesso público configurado.

Texto importado, fontes e justificativas são dados. Nenhuma URL dispara fetch no servidor; a interface usa escape do React e nunca injeta HTML bruto. Limite total de corpo: 128 KiB; anúncio: 50.000 caracteres. Respostas privadas têm `Cache-Control: no-store`. Logs de acesso com query strings foram desativados em Nginx/uvicorn; erros inesperados registram apenas correlação e tipo, sem exceção original, SQL ou corpo.

## Exportação

Na tela **Privacidade**, `Baixar exportação` baixa JSON autenticado com registros, snapshots e auditoria. Não inclui hashes de senha, cookies, tokens de sessão ou CSRF. O arquivo contém dados pessoais se estes tiverem sido cadastrados; guarde-o fora do Git. O endpoint é `GET /api/v1/candidate/export`.

## Eliminação administrativa

Remover um fato/evidência pela interface é exclusão lógica: o histórico continua disponível e análises ficam desatualizadas. Para apagar os dados da aplicação, incluindo snapshots, histórico, chaves de idempotência e sessões, use na raiz, **somente quando desejar essa eliminação**:

```powershell
uv run --project apps/api --env-file .env python -m jobhunter_api.manage erase --confirm DELETE_LOCAL_APPLICATION_DATA
```

A conta local e seu hash de senha são preservados para poder entrar novamente. Arquivos de origem em `.private/`, exportações e backups externos não são apagados por esse comando; não pertencem ao banco da aplicação. Exclua essas cópias separadamente se essa for a intenção. Nenhuma eliminação foi executada sobre dados reais durante o desenvolvimento: o teste usa banco isolado com dados fictícios.

As cópias antigas continuam existindo em backups até que sejam eliminadas; uma restauração deve respeitar eliminações posteriores. Recuperação e backups automatizados pertencem à fase 5.

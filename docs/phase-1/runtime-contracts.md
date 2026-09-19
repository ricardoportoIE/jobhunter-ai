# Contratos de runtime — fase 1

O OpenAPI em `/api/openapi.json` é a referência executável. Os schemas v0.2 da fase 0 permanecem como contratos de design e fixtures históricas; não são serializadores idênticos ao runtime. A implementação usa `version` para concorrência em todos os registros, UUID gerado pelo servidor e proprietário derivado exclusivamente da sessão.

## Decisões concretizadas

- Armazenamento: registros JSONB tipados/validados por Pydantic, metadados relacionais de owner/kind/version, índices para identidade e unicidade, snapshots separados e audit append-only. Não houve adoção de microserviços nem criação de pacotes vazios.
- Perfil: qualquer alteração de fato/evidência incrementa a versão e volta o perfil a draft. Publicação cria snapshot imutável. Fatos guardam versões das evidências; mudar uma evidência exige rever o fato antes de voltar a sustentar uma avaliação positiva.
- Evidência: `content_sha256` é hash do trecho/declaracão fornecido pelo usuário, não prova que um arquivo remoto foi baixado ou validado. Referências não abrem arquivos arbitrários.
- Vaga: importação conserva o texto integral e seu hash; edição substitui os campos estruturados e exige `expected_version`. `review_confirmed` libera PARSED. Estado SCORED é metadado derivado e não altera a versão dos campos revisados. Uma nova edição invalida a análise por comparação de versões.
- Matching: o usuário avalia critérios e liga fatos. Não há similaridade textual como prova de atendimento. Positivos sem fato válido tornam-se unknown. Estratégia de carreira usa avaliação explícita. Senioridade avançada confirmada em campo estruturado cria blocker; menções incidentais e nível misto não.
- Autorização: a exceção para eliminatório desconhecido só se aplica quando a categoria é autorização/horário e `future_authorisation=true`. Não é confirmação jurídica ou permissão para começar a trabalhar.
- Idempotência: o header `Idempotency-Key` é vinculado ao ator/operação/hash. Sem header, repetição exata do payload tem chave derivada. Payload diferente com a mesma chave retorna 409. Reimportação de uma identidade existente não sobrescreve conteúdo revisado.
- Deduplicação: ID+fonte, URL preservando parâmetros de identidade e hash normalizado+localidade. Não há merge semântico/fuzzy. Mesma referência com localidades conflitantes exige revisão; conteúdos iguais em cidades diferentes permanecem separados.
- Tracker: apenas estados efetivamente implementados são aceitos; etapas de geração/aprovação de pacote ficam para a fase 3. SHORTLISTED/RESEARCHED podem registrar SUBMITTED exclusivamente com confirmação, data, canal e comprovante de envio manual. Isso não chama email nem um portal.
- Falhas de ownership retornam 404 para não confirmar a existência do registro de outro proprietário. Falta de sessão retorna 401; origem/CSRF inválidos retornam 403. Erros têm código, mensagem segura e correlation ID.

## Rotas adicionais ao backlog

`GET /api/v1/session`, `POST /api/v1/candidate/profile/review`, `GET/PATCH/DELETE` de fatos/evidências, `GET /api/v1/jobs/{id}/matches`, `GET /api/v1/applications/{id}` e `GET /api/v1/candidate/export` completam o fluxo da interface. Login e healthchecks são os únicos endpoints de dados sem sessão; Swagger/OpenAPI também ficam disponíveis apenas no ambiente local.

Os dados reais da fase 0 não foram importados automaticamente. O seed fictício é opcional e recusa um perfil que já tenha fatos. Dados de teste usam bancos cujo nome começa por `jobhunter_test`.

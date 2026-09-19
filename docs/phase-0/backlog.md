# Backlog executável da fase 1

Escopo: núcleo local sem LLM. IDs são referências locais, não issues publicadas. Prioridade P0 = primeiro fluxo; P1 = completar a fase. Tamanho S/M/L é relativo, não estimativa de dias.

**P1-01 concluído localmente.** [Implementação e validação](../phase-1/p1-01-validation.md). Workflow de CI preparado; execução remota depende de hospedar o repositório no GitHub. Próxima entrega: P1-02.

| ID / prioridade / tamanho | História e entrega | Depende de | Critérios de aceitação |
|---|---|---|---|
| P1-01 / P0 / M | Como desenvolvedor, inicio API, web e PostgreSQL localmente | Revisão do ADR-001 | Docker Compose com healthchecks; .env.example sem segredos; versões/lockfiles; lint, types, testes e build em CI; portas locais |
| P1-02 / P0 / M | Como utilizador único, acesso meus dados com sessão autenticada | P1-01 | Login local, senha hash e secret fora do Git; sessão expira; ownership em endpoints; 401/403 e CSRF quando cookie testados |
| P1-03 / P0 / M | Registro fatos e evidências e publico versão do perfil | P1-02 | CRUD, migrations, validade/usos; fato verified exige revisão/evidência; revisão produz snapshot; exemplo fictício seed |
| P1-04 / P0 / M | Importo texto de vaga com origem e reviso requisitos | P1-02 | Conteúdo bruto com hash; URL não dispara fetch; campos desconhecidos null; confirmação manual precede PARSED; limites de tamanho e XSS |
| P1-05 / P0 / S | Evito repetir a mesma vaga/candidatura | P1-04 | ID externo+fonte, URL canônica e hash normalizado; teste de falso merge; import idempotente e conflito em payload diferente |
| P1-06 / P0 / L | Vejo score, coverage, gaps e blockers explicáveis | P1-03, P1-04 | ADR-003 v0.2; null sem dados; blocker confirmado vence score; sponsorship desconhecido não bloqueia procura; employment_gate separado; snapshots persistidos |
| P1-07 / P0 / M | Exploro Inbox e detalhe com evidências | P1-05, P1-06 | Filtros, estados vazio/erro/loading, links às evidências; score e coverage juntos; edição invalida análise; navegação por teclado |
| P1-08 / P1 / M | Acompanho shortlist e candidaturas manuais | P1-07 | Transições autorizadas, linha do tempo; registro manual autenticado e confirmado; nenhuma chamada de envio; duplicação impedida |
| P1-09 / P1 / M | Confio no histórico e protejo dados pessoais | P1-03, P1-08 | Evento atômico com mudança; papel sem update/delete em audit; logs redigidos; export/eliminação local e testes de rollback |
| P1-10 / P1 / M | Demonstro o fluxo completo de forma reproduzível | P1-07, P1-08, P1-09 | E2E fictício; smoke local; executar os 20 casos reais derivados; registrar divergências e revisão humana; checks CI passam |

## Ordem de execução

Primeiro P1-01 e P1-02. Em seguida perfil e importação, depois matching, Inbox/detalhe e tracker. Fechar com proteção de dados, fluxo ponta a ponta e documentação. Segurança de cada recurso acompanha sua história; P1-09 não adia autenticação ou redaction.

## Contratos de API a implementar

| Método / rota | Responsabilidade | Regra principal |
|---|---|---|
| POST /api/v1/session | Login | Limitar tentativas; segredo local |
| DELETE /api/v1/session | Logout | Invalidar sessão |
| GET, PATCH /api/v1/candidate/profile | Ler/editar perfil | Versionamento otimista |
| POST /api/v1/candidate/facts | Registrar fato | Não verificar automaticamente |
| POST /api/v1/candidate/evidence | Registrar referência | Caminhos nunca vêm como acesso arbitrário ao filesystem |
| POST /api/v1/jobs/import | Importar texto | Idempotency-Key; payload limitado |
| PATCH /api/v1/jobs/{id} | Rever campos | Esperar versão atual; conflito 409 |
| GET /api/v1/jobs e /jobs/{id} | Listar/detalhar | Paginação, filtros e ownership |
| POST /api/v1/jobs/{id}/analyse | Matching determinístico | Perfil/vaga versionados |
| GET /api/v1/matches/{id} | Resultado e evidências | Snapshot reproduzível |
| POST /api/v1/applications | Criar shortlist | Unicidade candidato/vaga |
| GET /api/v1/applications | Tracker | Filtros e paginação |
| POST /api/v1/applications/{id}/events | Transição/registro manual | Validar estado, ator e confirmação |

Formato uniforme de erro com código, mensagem e correlation ID; sem conteúdo sensível. Sem endpoint funcional de envio na fase 1. Contrato OpenAPI gerado pela implementação futura, não escrito como promessa de endpoint existente.

## Testes que fecham o primeiro slice

Migrations em PostgreSQL de teste; unitários de domínio/scoring e validade; API autenticada; idempotência e concorrência; proteção XSS; integração de auditoria; E2E importar → rever → analisar → abrir evidências. Incluir salário ausente, requisito eliminatório desconhecido/não atendido, fato revogado e perfil alterado. Não usar chamada paga em CI.

## Backlog posterior

Fase 2: adapter de inferência, parsing, benchmark do dataset e ledger de custo com reservas/limites €10 IA e €25 combinados. Fase 3: CV/carta e aprovação de pacote. Fase 4: piloto Greenhouse de leitura e Gmail em label dedicada, sem envio. Fase 5: Terraform temporário com preflight €15 AWS, TTL, exportação e teardown verificado. Fase 6: envio controlado em canal permitido. Esses itens não fazem parte da implementação da fase 1.

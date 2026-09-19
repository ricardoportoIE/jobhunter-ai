# JobHunter AI

Plataforma de inteligência de carreira que compara vagas com um perfil baseado em evidências e prepara candidaturas para revisão humana.

**Estado: núcleo da fase 1 implementado.** Login local, perfil e evidências versionados, revisão de vagas, matching determinístico, Inbox e tracker manual. A avaliação pública foi executada e tem divergências documentadas para revisão humana. O baseline continua local; IA e AWS pertencem às fases seguintes, com teto futuro de €25/mês.

## Iniciar localmente

Com Docker Desktop em modo Linux, Python e uv 0.12.7, execute na raiz:

```powershell
python scripts/init_env.py
docker compose up --build --detach --wait --wait-timeout 120
uv sync --project apps/api --locked
uv run --project apps/api --env-file .env python -m jobhunter_api.manage bootstrap
python scripts/smoke_local.py
```

Abra [a aplicação](http://127.0.0.1:5173). O utilizador é `local`; a senha inicial de login está em `.private/local-login.txt`. As credenciais do banco ficam em `.env`. Ambos são ignorados pelo Git. Para parar e preservar o banco: `docker compose down`.

Veja [desenvolvimento e testes](docs/local-development.md), [entregas por etapa](docs/phase-1/progress.md), [contratos de runtime](docs/phase-1/runtime-contracts.md), [avaliação dos 20 casos](docs/phase-1/evaluation-results.md) e [privacidade e eliminação](docs/phase-1/security-and-data.md).

## Começar pela fase 0

1. [Produto, escopo e métricas](docs/phase-0/product-brief.md)
2. [Encerramento e critérios de saída](docs/phase-0/discovery.md)
3. [Candidate Knowledge Base e master CV](docs/phase-0/candidate-knowledge-base.md)
4. [Fontes de vagas e dataset de avaliação](docs/phase-0/sources-and-evaluation.md)
5. [Arquitetura e estados](docs/architecture/overview.md)
6. [Contratos de dados](schemas/README.md)
7. [Modelo de ameaças](docs/security/threat-model.md)
8. [Wireframes das quatro telas iniciais](docs/phase-0/wireframes.md)
9. [Estimativa de custos](docs/phase-0/costs.md)
10. [Backlog priorizado da fase 1](docs/phase-0/backlog.md)
11. [Política de matching e autorização de início](docs/phase-0/matching-policy.md)
12. [Dataset real e limites da avaliação](docs/phase-0/evaluation-report.md)

## Decisões arquiteturais

- [ADR-001: monorepo e monólito modular](docs/adr/0001-modular-monolith.md)
- [ADR-002: IA, Bedrock, AgentCore e alternativas](docs/adr/0002-ai-runtime.md)
- [ADR-003: evidências, scoring e aprovação](docs/adr/0003-evidence-and-approval.md)
- [ADR-004: orçamento e AWS temporária](docs/adr/0004-local-first-budget.md)

Fluxo implementado: registrar evidências e fatos, publicar o perfil, importar texto de uma vaga, confirmar requisitos, avaliar atendimento, visualizar score/cobertura/lacunas e acompanhar candidatura manual. Parsing livre por IA entra na fase 2.

## Dados e validação

Exemplos em `data/fixtures/` são fictícios. `data/evals/real-cases.json` contém 20 anúncios reais reformulados e pseudonimizados, com rótulos de design feitos pelo assistente; não é um benchmark executado ou gold set humano. CV, 114 fatos, 43 evidências, contatos, restrições e originais das vagas ficam em `.private/`, ignorado pelo Git.

Validação documental e de schemas:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-phase0.txt
.venv\Scripts\python scripts/validate_phase0.py
.venv\Scripts\python scripts/validate_phase0.py --private
```

O comando com `--private` valida também os dados privados nesta máquina e não se aplica a clones sem `.private/`. Os testes da aplicação estão no guia de desenvolvimento. Não há deploy cloud, recursos AWS, integração de email ou envio de candidatura configurados. O piloto humano e a preparação da fase 2 são os próximos passos.

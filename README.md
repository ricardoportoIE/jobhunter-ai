# JobHunter AI

Plataforma de inteligência de carreira que compara vagas com um perfil baseado em evidências e prepara candidaturas para revisão humana.

**Estado: fase 0 e P1-01 concluídos.** Estrutura local com React/TypeScript, FastAPI e PostgreSQL, healthchecks, testes e workflow de CI. O baseline é local, com teto de €25/mês para uso futuro de AWS e IA e demonstrações cloud temporárias. Autenticação, perfil e vagas entram nas próximas entregas.

## Iniciar localmente

Com Docker Desktop em modo Linux e Python 3.13 ou superior, execute na raiz:

```powershell
python scripts/init_env.py
docker compose up --build --detach --wait --wait-timeout 120
python scripts/smoke_local.py
```

Abra [a aplicação](http://127.0.0.1:5173) ou [a documentação da API](http://127.0.0.1:5173/api/docs). A senha local é gerada em `.env`, sem sobrescrever arquivo existente. Para parar e preservar o banco: `docker compose down`.

Veja [desenvolvimento local e comandos de verificação](docs/local-development.md) e [evidências de conclusão do P1-01](docs/phase-1/p1-01-validation.md).

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

Primeira entrega funcional planejada: importar texto de uma vaga, confirmar requisitos estruturados, comparar com fatos verificados e visualizar score, lacunas e evidências. Parsing livre por IA entra na fase 2.

## Dados e validação

Exemplos em `data/fixtures/` são fictícios. `data/evals/real-cases.json` contém 20 anúncios reais reformulados e pseudonimizados, com rótulos de design feitos pelo assistente; não é um benchmark executado ou gold set humano. CV, 114 fatos, 43 evidências, contatos, restrições e originais das vagas ficam em `.private/`, ignorado pelo Git.

Validação documental e de schemas:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-phase0.txt
.venv\Scripts\python scripts/validate_phase0.py
.venv\Scripts\python scripts/validate_phase0.py --private
```

O comando com `--private` valida também os dados privados nesta máquina e não se aplica a clones sem `.private/`. Esses comandos validam artefatos de design; os testes da aplicação estão no guia de desenvolvimento. Não há deploy cloud, recursos AWS, integração de email ou submissão configurados. O próximo passo é P1-02: sessão autenticada para utilizador único.

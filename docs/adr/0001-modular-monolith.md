# ADR-001 — Monorepo e monólito modular

Estado: adotado como baseline da fase 1. Data: 2026-09-19.

## Contexto

Um desenvolvedor, um utilizador e um fluxo inicial pequeno precisam evoluir contratos e interface juntos. O briefing descreve muitos serviços lógicos, mas isso não exige processos separados.

## Decisão

Usar monorepo com backend FastAPI modular, frontend React/TypeScript e PostgreSQL. Manter domínio separado dos adaptadores. Criar apenas os pacotes que já tenham responsabilidade implementada; não copiar toda a árvore futura do briefing.

## Alternativas

| Alternativa | Vantagem | Custo neste estágio |
|---|---|---|
| Monólito sem módulos | Menos estrutura inicial | Regras, infraestrutura e provider se misturam |
| Monólito modular escolhido | Transações simples, contratos coordenados, deploy pequeno | Exige disciplina de dependências |
| Microserviços | Deploy e escala independentes | Rede, observabilidade distribuída e consistência antes de haver necessidade |
| Repositórios separados | Autonomia de equipes | Não há equipes independentes; mudanças de contrato ficam mais difíceis |

## Consequências e revisão

Módulos compartilham banco com acesso por serviços/repositórios próprios. Renderização pesada e ingestão poderão virar workers usando o mesmo domínio. Extrair serviço somente se isolamento de segurança, carga ou ciclo de deploy medido exigir. A primeira fase não instala LangGraph, Redis, Celery, MCP ou pgvector.

P1-01 implementa `apps/api` (Python 3.13, FastAPI, psycopg) e `apps/web` (Node 24, React 19, TypeScript 6, Vite 8), com PostgreSQL 17. TypeScript 6 respeita o intervalo suportado pelo typescript-eslint selecionado. `uv.lock` e `package-lock.json` fixam as dependências resolvidas; imagens Docker e ações de CI usam digests/SHAs. O ambiente Python da API fica separado do validador documental da fase 0.

Neste incremento, a API contém apenas configuração, conexão de banco e healthchecks. Não há tabelas de domínio, migrations ou importação de dados privados. O frontend acessa `/api` na mesma origem: Nginx no Compose e proxy do Vite no modo de desenvolvimento. Portas publicadas ficam em `127.0.0.1`; credencial aleatória fica em `.env` ignorado. Detalhes operacionais em [desenvolvimento local](../local-development.md).

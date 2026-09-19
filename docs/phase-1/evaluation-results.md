# Avaliação executada — fase 1

Foram executados os 20 casos públicos derivados de anúncios reais, usando o motor `deterministic-manual-0.2.0` e a identidade conservadora de vagas. [Resultado reproduzível](../../data/evals/phase1-results.json). Comando: `uv run --project apps/api python scripts/evaluate_phase1.py --check`.

## Escopo e resultados

Este é um baseline conservador de dados públicos, **sem perfil privado e sem avaliações positivas inventadas**. O adapter usa campos já estruturados (título, nível e skills mencionadas); não extrai semântica livre nem transforma labels esperados em entradas. A fase 1 depende de revisão manual para estruturar requisitos e avaliar atendimento. O teste não mede aderência ao CV real, precisão de parsing por IA ou empregabilidade.

| Verificação | Resultado |
|---|---|
| Casos executados | 20: 12 development e 8 evaluation |
| Blockers esperados, score desconhecido e revisão antes de começar | 20/20 |
| Concordância de recomendação após mapear taxonomias | 12/20 |
| Casos com alguma diferença de recomendação, flags ou duplicação | 18/20 |
| Gold humano | Não disponível; revisão humana pendente |

O conjunto original usa `DEPRIORITISE`, `SECONDARY` e `PURSUE_WITH_REVIEW`, que não são os enums do score v0.2. O relatório declara o mapeamento usado para comparação. Os 12/20 não são uma medida de precisão do produto.

## Divergências registradas

- REAL-05/06/07/18: rótulos sugerem despriorização por experiência ou formação. Sem fatos revisados e avaliação explícita, o motor mantém REVIEW, score null e cobertura zero. Nenhum portfólio é convertido automaticamente em anos de emprego ou diploma.
- REAL-10: o rótulo permite perseguir a vaga junior. O motor conserva REVIEW sem um perfil avaliado; sponsorship ausente não cria blocker.
- REAL-11/13/16: a prioridade secundária de carreira precisa de avaliação explícita. O motor não inventa preferências.
- REAL-11/13: as reformulações públicas têm textos diferentes e não incluem IDs/URLs de origem. A identidade conservadora não confirma a duplicata anotada documentalmente. Unificação entre boards com boilerplate diferente exige revisão manual ou uma etapa posterior de detecção de candidatos a duplicata.
- Flags como conflito título/corpo, matrícula, B2B, janela de graduação, clearance e falta de MSc exigem requisitos/avaliações revisados. O baseline não implementa parsing livre fora do escopo da fase 1.
- Níveis explicitamente senior/staff são bloqueados; vagas de níveis mistos permanecem para revisão. Texto incidental como “colaborar com senior engineers” não aciona o bloqueio.

## Revisão humana

Cada caso tem campo `human_review.status=pending` no relatório. Nenhuma decisão humana foi presumida. O revisor deve confirmar as diferenças acima, corrigir requisitos/avaliações quando necessário e registrar concordância ou discordância com justificativa. As labels originais continuam preservadas; não foram ajustadas para melhorar resultados.

O fluxo funcional completo com um perfil fictício e avaliações explícitas é verificado separadamente por testes de integração e E2E. Esse fluxo prova execução e rastreabilidade, não substitui o piloto humano com dados reais.

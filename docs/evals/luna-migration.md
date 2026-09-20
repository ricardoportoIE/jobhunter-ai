# Matching com Luna high — implementação e evidências

Entrega local em 20/09/2026. Matching e segunda avaliação usam `gpt-5.6-luna` com
`reasoning.effort=high`. Extração e estratégia P3 continuam com GPT-4.1 mini;
Luna também foi testado nessas tarefas. A pesquisa pública usa Luna high com `web_search`.
A decisão combina os resultados anteriores e os testes abaixo; o conjunto novo de matching
isolado empatou e não demonstra superioridade geral de inteligência.

## Comportamento implementado

- Adapter Responses diferencia modelos de raciocínio de GPT-4.1: Luna recebe `reasoning`,
  sem `temperature`; mini recebe temperatura zero. Sem retries automáticos ou fallback.
- Contrato `structured-ids-1.0`: IDs de fatos, evidências e requisitos são enumerados a partir
  da entrada. A validação posterior continua verificando propriedade, vínculo, citações literais,
  usos permitidos e validade. Grupos com mais de 250 IDs usam a validação posterior, para limitar
  o tamanho do contrato. IDs válidos não comprovam a interpretação semântica da resposta.
- Cache distingue conteúdo, schema efetivo, versão de contrato, modelo, esforço, prompt,
  limite de saída e ferramentas. Segunda avaliação usa outra operação, preservando ambas.
- Reservas incluem a saída de raciocínio e até três chamadas web. Uso desconhecido ou acima
  da reserva bloqueia novas chamadas até reconciliação. Entrada em cache é contabilizada pelo
  preço normal, conservadoramente; tokens de raciocínio já integram a saída, sem dupla cobrança.
- Pesos e cálculo continuam no motor determinístico. Bloqueio explícito não é compensado por
  competências desejáveis. Buscar uma oferta e poder iniciar trabalho continuam separados.
- Pendências de título/corpo, evidências contraditórias e requisitos eliminatórios não confirmados
  impedem priorização. Uma anotação não transforma um requisito desconhecido em atendido.
  Esclarecimentos registram conclusão, fonte, responsável e versões. Bloqueios confirmados continuam.
- Avaliações diferentes sobre a mesma entrada aparecem lado a lado. O servidor verifica o histórico
  mesmo quando a análise omite `ai_run_id`. Nova divergência também desatualiza uma análise anterior.
- Pesquisa web é uma ação explícita: transmite a pergunta pública e os domínios autorizados,
  sem adicionar perfil, vaga ou documentos ao pedido. Retorna citações clicáveis, hora da consulta
  e pendências; não altera fatos nem score. Histórico de uma hora é marcado para nova consulta.
  A hora da consulta não prova a data de atualização da página nem a correção de uma interpretação.

## Configuração por tarefa

| Tarefa | Prefixo após `JOBHUNTER_AI_` | Modelo local |
|---|---|---|
| Extração | `PARSING_` | `gpt-4.1-mini-2025-04-14` |
| Matching | `MATCHING_` | `gpt-5.6-luna` high |
| Segunda avaliação | `REVIEW_` | `gpt-5.6-luna` high |
| Estratégia | `STRATEGY_` | `gpt-4.1-mini-2025-04-14` |
| Pesquisa pública | `RESEARCH_` | `gpt-5.6-luna` high |

Cada prefixo aceita `MODEL`, `EFFORT` e `PROMPT_SUFFIX`. Por exemplo,
`JOBHUNTER_AI_REVIEW_MODEL=gpt-4.1-mini-2025-04-14` permite uma segunda avaliação com mini.
Esforço só é enviado para Luna. Sufixos de prompt são orientação do operador, até 4.000 caracteres,
acrescentada às instruções-base; seu hash altera a versão e o cache. Não coloque segredos neles.
As regras de fonte, propriedade, orçamento e cálculo continuam no código.

Templates-base: parsing `job-parser-1.3`, matching `evidence-matching-1.2`, estratégia
`application-strategy-1.1`, pesquisa `public-research-1.0`. `JOBHUNTER_AI_MODEL` permanece como
fallback legado. Modelos novos exigem cadastro de preço/capacidades, testes de contrato e avaliação;
a aplicação não aceita um identificador arbitrário nem promove modelos automaticamente.

Luna usa até 8.000 tokens de saída por padrão, incluindo raciocínio; limite configurável de 1.000
a 16.000. Mini permanece em 5.000. Timeout da API: 180s; Nginx: 240s. Esses limites afetam cache.

## Avaliação nova e resultados reais

[Holdout congelado](../../data/evals/migration-holdout.json) no commit `5ced489`, antes das chamadas:
oito casos sintéticos novos, dois modelos, duas execuções por caso. Inclui anúncio longo,
requisitos combinados e alternativos, mínimo numérico, diploma versus MSc, conflito de evidências,
título/corpo divergentes e comandos maliciosos no anúncio. Os rótulos são do assistente.

| Matching final, 16 respostas por modelo | GPT-4.1 mini | Luna high |
|---|---:|---:|
| Respostas válidas | 16 | 16 |
| Status iguais ao rótulo original | 14 | 14 |
| Positivos sem sustentação nos critérios rotulados, antes dos filtros | 0 | 0 |
| Status alterados pelos filtros | 0 | 0 |
| Casos com status diferente entre repetições | 0 | 0 |
| Esclarecimentos adicionais onde o rótulo não os exigia | 0 | 3 |

**Defeito no rótulo H05:** o texto declara que nunca houve implantação em produção, mas o rótulo
foi congelado como `unknown`. Ambos responderam `unmet` nas duas repetições, coerente com a negativa
explícita. Preservamos dataset e contagem 14/16; não corrigimos o gabarito depois para aumentar a nota.
As três sinalizações adicionais de Luna são custo de revisão a examinar, não vantagem presumida.
Estabilidade aqui mede status em somente duas repetições, não toda a redação ou todos os alertas.

O fluxo HTTP usa banco `jobhunter_test_migration` e candidato fictício, passando pelas rotas reais:
extrair → preencher rascunho → revisão simulada → matching → cálculo → seleção de fatos P3 →
aprovar estratégia → gerar documentos → aprovar → baixar ZIP/DOCX/PDF → invalidar fonte.
Todas as chamadas pagas reservam custo também no ledger principal; o banco descartável não evade
o limite mensal. O perfil pessoal não é alterado. As aprovações são etapas explícitas do teste,
não aprovações do utilizador sobre uma candidatura real.

| Fluxo HTTP final | GPT-4.1 mini | Luna high |
|---|---|---|
| Anúncio longo, sem conflito | Completo | Completo |
| Título/corpo contraditórios | Matching rejeitado pelo validador | Completo, recomendação `REVIEW` |

No caso rejeitado, mini classificou uma divergência do anúncio como conflito entre evidências e
forneceu apenas um fato, violando o contrato semântico. Nenhum score ou documento desse fluxo foi
produzido. A falha permanece no relatório; não repetimos até obter uma resposta favorável.

Antes da restrição por enum, uma chamada Luna trocou um caractere do UUID de um fato. O validador
barrou a referência inexistente. Essa falha motivou o contrato novo e a repetição integral com
ambos os modelos, mantendo o [baseline](../../data/evals/migration-live-baseline.json).
O baseline também preserva quatro interrupções por erro do executor de teste ao omitir campos
na revisão e uma extração Luna que deixou o cargo nulo diante do conflito. A revisão simulada
subsequente registra preenchimentos manuais separadamente; eles não contam como acerto do modelo.

O teste web real fez uma chamada Responses com três buscas, limitada a fontes oficiais irlandesas.
Retornou a página de Critical Skills Employment Permit e explicitou não ter confirmado a data
editorial, sem decidir elegibilidade individual. O servidor validou domínios, intervalos de
citação, uso e custo. O resultado continua sujeito à conferência humana.

Artefatos: [resultado final e respostas brutas](../../data/evals/migration-live.json),
[executor](../../scripts/evaluate_migration.py). Total desta entrega: **93 chamadas Responses**
(49 baseline + 44 finais), incluindo três chamadas internas de busca web.
Custo contabilizado: **€0,17025100** (€0,06787750 + €0,10237350), com margem 1,25 EUR/USD;
é estimativa conservadora do projeto, não fatura ou cotação cambial.

## Decisões reais do utilizador

[Três rótulos explícitos](../../data/evals/user-decisions.json), separados do gabarito sintético:

- REAL-01: descartar. O motivo informado, estudar em Dublin, não está confirmado no snapshot;
  guardado como justificativa do utilizador a verificar, sem virar requisito factual da vaga.
- REAL-10: priorizar; objetivo do projeto.
- REAL-12: manter no escopo, com esclarecimento da função devido ao título/corpo divergentes.

São decisões sobre snapshots históricos. Não provam que as ofertas continuam abertas nem formam
um gold set completo de elegibilidade. Não foram enviadas ao modelo como respostas esperadas.

## Verificação e reavaliação

Checks locais: 89 testes API, 13 React e seis fluxos Playwright desktop/mobile com Edge;
tipagem, lint, build Docker e smoke local. Playwright inclui busca citada e segunda avaliação
com divergência. DOCX/PDF preservaram literalmente o fato aprovado; downloads de fontes alteradas
foram bloqueados. O layout de documentos P3 permanece o já verificado na fase anterior.

```powershell
uv run --project apps/api python scripts/evaluate_migration.py --check
uv run --project apps/api python scripts/compare_reasoning_models.py --check
uv run --project apps/api python scripts/compare_reasoning_models.py --check --protocol refined
```

`evaluate_migration.py --live` é explícito, limita a reserva adicional a €1 por execução, mantém
sucessos existentes e preserva falhas. `--retry-pipeline` só deve ser usado após diagnosticar a causa;
arquiva tentativas anteriores no relatório. Para outra rodada, preserve o relatório anterior e
congele novas entradas/rótulos antes de consultar os modelos. Não reutilize este holdout como
prova independente depois de ajustar prompts com base nele.

Critérios de promoção: primeiro erros críticos, afirmações sem sustentação, consistência e trabalho
de revisão; depois adequação por tarefa. Preço e latência são operacionais. Nenhuma amostra pequena
garante ausência de limites de raciocínio ou de erros futuros. O alias Luna pode mudar: registre
modelos, esforço, prompt, contrato, respostas brutas e novas decisões humanas em cada rodada.

Preços conferidos em 20/09/2026: [Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna)
US$0,20/M entrada e US$1,20/M saída; [busca web](https://developers.openai.com/api/docs/pricing)
US$10/1.000 chamadas, mais tokens de conteúdo. O uso segue a
[API de busca web](https://developers.openai.com/api/docs/guides/tools-web-search).

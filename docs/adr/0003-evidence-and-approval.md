# ADR-003 — Evidências, score e aprovação

Estado: adotado para implementação da fase 1; refinado pelas preferências confirmadas. Data: 2026-09-19.

## Decisão proposta

Fatos versionados e evidências aprovadas são a fonte factual. LLM pode extrair ou explicar, mas não cria fatos nem altera score. Aprovação de pacote e autorização de envio são objetos distintos vinculados a versões.

## Scoring v0.2

Pesos do briefing: skills 30, experiência 20, portfólio 15, educação 10, localização/modalidade 10, salário 5, autorização/horário 5 e estratégia 5; soma 100.

Cada categoria contém critérios explicitamente estruturados e revisados. Por critério: `met=1`, `partial=0.5`, `unmet=0`; `unknown` não entra na média. Critérios obrigatórios têm peso interno 2 e desejáveis 1. Similaridade textual não prova atendimento. Estratégia usa avaliação explícita do utilizador, nunca uma preferência inventada.

Para categoria c: `attainment_c = soma(peso_i × atendimento_i) / soma(peso_i conhecido)`; se nada conhecido, é null. `coverage_c = soma(peso_i conhecido) / soma(peso_i aplicável)`. Categoria sem critérios recebe coverage 0 e attainment null nesta primeira versão; o revisor deve preencher requisitos relevantes antes de confiar no resultado.

`effective_weight_c = category_weight_c × coverage_c`.

`score = 100 × soma(effective_weight_c × attainment_c) / soma(effective_weight_c)`; null se denominador zero. `coverage = soma(effective_weight_c) / 100`. Arredondamento decimal half-up para 2 casas, somente no resultado final. Mostrar score e coverage lado a lado para não apresentar análise parcial como completa.

Exemplo: skills com attainment 0.8 e coverage 1, experiência com attainment 0.5 e coverage 1, demais categorias desconhecidas → score 68, coverage 0.5 → `REVIEW`, sem recomendação positiva automática.

Requisito eliminatório explicitamente não atendido → `BLOCKED`, independentemente do score. Eliminatório desconhecido (exceto possibilidade futura de autorização/sponsorship) ou coverage < 0.70 → `REVIEW`. Sem essas condições: 85–100 `PRIORITISE`; 70–84 `APPLY_AFTER_REVIEW`; 55–69 `REVIEW`; abaixo de 55 `TRACK_OR_ARCHIVE`. A lista de blockers preserva a razão e evidência. Informação ausente não equivale a blocker confirmado.

Autorização para iniciar e recomendação de procurar a oferta são dimensões distintas. Sponsorship desconhecido, necessidade de nova permissão ou limite atual de horas não bloqueiam por si só a procura full-time. Registrar `employment_gate=REVIEW_BEFORE_START` e flags; só incompatibilidade explícita confirmada constitui blocker. Aplicar a [política de matching v0.2](../phase-0/matching-policy.md). Não considerar esse desconhecido como atendimento; a categoria de autorização mantém coverage desconhecida.

São decisões de produto a calibrar. Snapshot da vaga/perfil, evidências, pesos, algoritmo e avaliações de critérios devem bastar para reproduzir o resultado; a versão do algoritmo identifica também aliases de skills e regras de arredondamento.

## Aprovação

Objeto futuro `Approval`: ID, ator autenticado, escopo (`package` ou `submission`), application ID, versões de perfil/vaga, hash do pacote, destinatário/canal quando envio, instante, expiração e decisão. Rejeição de pacote não vira rejeição pelo empregador.

Transição e evento de auditoria são atômicos. Aprovação repetida é idempotente; alteração de payload invalida a decisão. Campos sensíveis requerem revisão explícita por campo. Nenhuma aprovação pode ser criada ou ampliada por um LLM.

## Alternativas e consequências

Score totalmente delegado a LLM foi descartado por dificultar reprodução. Guardar apenas o CV foi descartado por não permitir origem por afirmação. Exigir evidências e snapshots acrescenta revisão inicial, mas permite explicar e invalidar pacotes corretamente.

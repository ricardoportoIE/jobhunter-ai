# Product brief — fase 0

Data: 2026-09-19. Estado: definição da fase 0 consolidada após análise do CV, preferências fornecidas e confirmação factual do utilizador.

## Problema e público

Uma pessoa em transição para engenharia de software precisa reunir vagas, avaliar compatibilidade e adaptar candidaturas sem perder consistência factual. O primeiro público é um candidato a oportunidades graduate/junior, priorizando backend Python/Java, depois software/full-stack e IA aplicada. Irlanda, especialmente Dublin, precede o Reino Unido. A busca é full-time, com requisitos de início revistos separadamente. Recrutadores são audiência do portfólio, não utilizadores do MVP.

O trabalho principal do produto é responder: «Vale a pena investir nesta candidatura, com base no que consigo comprovar e nas minhas restrições?».

## Escopo por entrega

| Entrega | Incluído | Critério de sucesso |
|---|---|---|
| Fase 1: núcleo local | Perfil factual, empresas, importação de texto, edição estruturada, scoring determinístico, evidências, tracker, autenticação local e auditoria | Uma vaga percorre importação → revisão dos requisitos → score reproduzível → dashboard |
| Fases 2–3: MVP funcional | Parsing por IA, deduplicação semântica quando útil, CV/cover letter, validação factual e revisão humana | Pacote aprovado aponta para versões específicas das evidências |
| Fase 4: descoberta | Email opt-in e um conector de API permitido, pesquisa de empresa e alertas | Uma fonte habilitada produz oportunidades rastreáveis |
| Fase 5: demonstração AWS temporária | Infraestrutura reproduzível, backups, custos e observabilidade | Deploy validado, evidências capturadas e recursos destruídos; uso cotidiano local |
| Fase 6: orquestração | Um canal permitido ou sandbox com confirmação final | Nenhum envio sem aprovação específica e válida |

Ficam fora do MVP: multi-tenancy, billing, mobile, dezenas de conectores, modelos próprios, envio em massa e automação no LinkedIn.

## Restrições de produto

- Conteúdo de vaga é dado não confiável, nunca instrução para ferramentas.
- Uma afirmação só pode sustentar um documento se estiver verificada, vigente e autorizada para aquele uso.
- Dados desconhecidos aparecem como desconhecidos. Não inferir autorização de trabalho, sponsorship, salário ou experiência.
- Requisitos eliminatórios são avaliados separadamente do score.
- Campos sensíveis exigem revisão específica; a aprovação do pacote não equivale à aprovação de envio.
- Inglês britânico nos documentos de candidatura; documentação técnica inicialmente em português.

## Métricas propostas — ainda sem baseline

| Métrica | Como medir | Meta inicial proposta |
|---|---|---|
| Tempo ativo por análise | Cronometrar 5 análises manuais e 5 com o produto, mesmas tarefas | Reduzir mediana em 50% |
| Concordância com a recomendação | Revisão humana de 20 vagas, registrar divergências | Pelo menos 16/20 após calibração |
| Reprodutibilidade | Mesmo snapshot de perfil, vaga, pesos e algoritmo | Resultados idênticos |
| Cobertura factual de documentos | Afirmações factuais com evidência aprovada / total de afirmações | 100%; bloquear geração final se falhar |
| Envios indevidos | Envio sem aprovação válida ou duplicado | Zero |
| Custo | Ledger de tokens + relatório AWS por ambiente | €25/mês combinado: €15 AWS e €10 IA |

As metas são critérios de aceitação propostos, não resultados alcançados. Taxas de entrevista e resposta serão acompanhadas sem atribuir causalidade ao score numa amostra pequena.

## Decisões consolidadas

Preferências, master CV e orçamento fornecidos; o utilizador confirmou fatos e datas atuais. Piso salarial e limite de relocação permanecem não definidos por escolha explícita, sem filtro eliminatório. Gmail é o primeiro provider de alertas, a integrar apenas na fase 4. Métricas acima são alvos de engenharia do piloto; seus baselines ainda serão medidos. Ver [discovery](discovery.md) e [matching](matching-policy.md).

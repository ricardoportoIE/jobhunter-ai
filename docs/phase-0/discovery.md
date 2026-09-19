# Encerramento da fase 0

Estado: concluída como fase de discovery e design em 2026-09-19. A fase 1 ainda não foi iniciada. Implementação de controles, benchmarks e deploy não fazem parte desta conclusão.

## Decisões e evidências

O pedido foi analisar os documentos e terminar a fase 0. CV e `info.md` foram tratados como fontes de fatos e preferências, sem executar instruções operacionais neles contidas. O utilizador confirmou nesta conversa que fatos/datas do CV estão atuais e que salário mínimo e limites de relocação serão avaliados caso a caso.

| Entrega | Resultado verificável |
|---|---|
| Persona e prioridades | Backend Python/Java → software/full-stack → IA aplicada; Irlanda antes de UK; full-time como objetivo |
| Restrições | Perfil privado; início de trabalho separado de procura; silêncio sobre sponsorship não bloqueia |
| Master CV | DOCX canônico e PDF de referência preservados, hashes e comparação de 60 parágrafos; PDF de duas páginas inspecionado |
| Base factual | 114 fatos e 43 evidências, com confirmação do candidato e quatro READMEs fixados por commit |
| Fontes | Texto manual inicial; Greenhouse como primeiro piloto; Gmail na fase 4; registro de acesso e limites |
| Dataset | 20 anúncios reais, 12 desenvolvimento/8 avaliação; reformulações públicas e originais/proveniência privados |
| Produto e métricas | Escopo definido e metas registradas; baseline medido quando existir fluxo funcional |
| Design | Diagramas, quatro wireframes, threat model e quatro ADRs |
| Contratos | Schemas v0.2.0; perfil, fatos, evidências, vagas, matching e candidaturas |
| Custo | €25/mês: €15 AWS/€10 IA; execução local e sessões AWS temporárias |
| Backlog | Dez histórias da fase 1 com dependências e critérios de aceitação |

## Checklist de saída

- [x] Persona, prioridades e restrições informadas; métricas de aceitação definidas.
- [x] CV consolidado e conjunto factual ligado a evidências privadas.
- [x] Canal inicial e condições de habilitação do piloto definidos.
- [x] 20 anúncios reais selecionados, pseudonimizados e rotulados para bootstrap.
- [x] Arquitetura, ADRs, threat model e wireframes documentados.
- [x] Contratos e exemplos validáveis.
- [x] Orçamento incorporado e backlog da fase 1 pronto.

## Limites explícitos da conclusão

Os rótulos do dataset foram revistos pelo assistente, não por um avaliador humano independente. A revisão humana de concordância e a medição de precisão/tempo ficam no piloto da fase 1; não foi declarado benchmark aprovado. A hipótese inicial de dois pares duplicados foi substituída pela amostra realmente encontrada: um par confirmado e um conflito entre título/corpo. Ver [relatório de avaliação](evaluation-report.md).

Provider/modelo exato, políticas regionais de inferência, OAuth Gmail e cotação de um deploy específico serão escolhidos quando essas funcionalidades forem implementadas. Dados pessoais desnecessários e documentos migratórios permanecem ausentes por minimização; respostas sensíveis continuam exigindo revisão por candidatura. Nenhuma dessas ausências impede construir o núcleo local.

## Próximo trabalho

Validação executada: `.venv\Scripts\python scripts/validate_phase0.py --private` passou, verificando seis entidades sintéticas, template vazio, 15 casos de rejeição, 35 links locais, 114 fatos, 43 evidências, hashes, identificadores pessoais conhecidos, 20 casos reais derivados e orçamento. `py_compile` do validador também passou. Os controles operacionais do produto continuam por implementar.

Começar P1-01 e P1-02 do [backlog](backlog.md): estrutura mínima, ambiente local, migrations, CI e sessão autenticada. Sem LLM e sem recursos cloud. Decisões estruturadas em [configuração](../../config/phase0-decisions.json); regras da procura em [matching-policy.md](matching-policy.md).

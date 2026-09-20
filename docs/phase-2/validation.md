# Validação de P2 — 2026-09-20

**P2-01 a P2-08 concluídos para uso local com revisão humana.** Após o utilizador adicionar
US$10 e autorizar os testes, executamos chamadas reais de parsing, matching e embeddings.
GPT-4.1 mini permanece como padrão, agora com comparação registrada. Nenhum CV ou fato real
do candidato foi enviado nesses testes. A chave permanece exclusivamente no backend.

## Benchmark real

20 casos públicos derivados, dois modelos, prompt/normalizador `job-parser-1.3`.
[Resultados completos e revisão](../../data/evals/phase2-benchmark.json).

| Modelo | Saídas válidas | Campos básicos corretos nas válidas | p50 / p95 | Custo contabilizado |
|---|---|---|---|---|
| GPT-4.1 mini | 20/20 (100%) | 79/80 (98,75%) | 2,559 / 3,351 s | €0,02443300 |
| GPT-4.1 nano | 18/20 (90%) | 71/72 (98,61%) | 2,276 / 2,823 s | €0,00610580 |

Os campos são título, empresa, local e país; o denominador de nano exclui duas respostas
rejeitadas. Contando falhas como campos incorretos, nano obtém 71/80 (88,75%). Nenhuma recusa.
Todas as citações aceitas foram verificadas por substring e offsets. Gates: ≥95% de saídas
válidas e ≥95% de campos básicos. Mini passa ambos; nano falha no primeiro.

Revisão documental pelo assistente, **não gold humano**:

- REAL-12: mini abreviou o título anotado; permanece contado como erro. Sinalizou a
  contradição título/corpo. Não alteramos o rótulo para melhorar a métrica.
- REAL-17: nano declarou sponsorship disponível, perdendo a restrição a certos cargos.
  Mini manteve desconhecido e apresentou o trecho condicional para revisão.
- REAL-11: salário sem valor numérico permanece desconhecido. Uma explicação literal da
  ausência vira nota de revisão, sem criar montante ou confiança num valor inexistente.
- Importância, categoria, completude de requisitos e interpretação de texto contextual
  ainda exigem correção humana, inclusive no mini. Exemplos: REAL-03/07/08/14/18.

Foram preservadas as execuções anteriores: [1.0](../../data/evals/phase2-benchmark-baseline.json),
[1.1](../../data/evals/phase2-benchmark-1.1.json) e [1.2](../../data/evals/phase2-benchmark-1.2.json).
Elas revelaram objetos de salário vazios, citações reconstruídas e confusão entre ausência
de valor e evidência da ausência. A normalização só aceita trechos literais e mantém nulos;
citações inventadas e valores sem suporte continuam rejeitados.

Os mesmos 12 casos de desenvolvimento e 8 de avaliação foram repetidos durante os ajustes;
**o conjunto de avaliação já não é um holdout intocado**. Precisão de matching pessoal,
calibração da confiança e concordância humana precisam de novos casos revisados no piloto.
Isso limita conclusões de qualidade geral, sem impedir o uso assistido e revisado do P2.

## Aceitação funcional

| Verificação | Resultado |
|---|---|
| Python/API/PostgreSQL | 57 testes aprovados |
| Componentes React | 11 testes aprovados |
| Playwright desktop/mobile | 4 fluxos completos aprovados, provedor sintético isolado |
| Ruff, formatação e mypy estrito | Aprovados |
| ESLint, Prettier, TypeScript, Vite e wheel | Aprovados na implementação; sem alteração de frontend nesta conclusão |
| Compose, migrations, runtime restrito, proxy e smoke | Aprovados; serviços saudáveis |
| Parsing real adversarial | Salário extraído; instrução maliciosa sinalizada; sponsorship não inventado |
| Matching real com evidência fictícia | Python suportado; emprego comercial, autorização e carreira desconhecidos |
| Embeddings reais | 256 dimensões; resultado Python acima de cozinha; cache sem nova cobrança |
| HTTP real em Docker/Nginx | Login/CSRF → extração → cache → rascunho → revisão → índice → busca → duplicado → arquivo |
| Dados do utilizador | Perfil inalterado; vagas fictícias arquivadas; sessão de teste encerrada |
| Segredo em arquivos versionáveis, histórico Git e assets web | Não encontrado na verificação exata |

Artefatos: [provas de IA](../../data/evals/phase2-live-acceptance.json) e
[fluxo HTTP](../../data/evals/phase2-http-acceptance.json). Matching foi exercitado pelo serviço
real com a mesma validação/ledger; sua integração HTTP e o score revisado estão cobertos no
E2E sintético. Não confundimos transporte simulado com qualidade de inferência real.

Cobertura adicional: autenticação, CSRF, ownership, citações inventadas, schemas inválidos,
recusas, saídas incompletas, injeção como dado, reservas concorrentes, retries/cache, limite
combinado, preços vencidos, timeout, virada do mês, reconciliação, eliminação durante
inferência, versões de embeddings, conflitos entre cidades e consentimento por evidência.
O fluxo manual de P1 continua coberto.

## Consumo e fechamento

Ledger do projeto após todos os testes: **€0,13299404**, aproximadamente **US$0,1064** aos
preços registrados. Inclui quatro comparações de 40 chamadas, diagnósticos e testes reais,
inclusive 38 respostas rejeitadas. São 138 sucessos, 38 inválidas e os dois HTTP 429 iniciais
sem tokens. Reservas pendentes: €0; custos desconhecidos: nenhum. A conversão local de
€1,25/US$ é margem contábil; esses números não são consulta da fatura ou do saldo da carteira.

Teto de IA €10/mês e combinado €25 preservados. A reserva contábil de €15 para AWS não é
consumo AWS. Sem publicação, candidatura ou mensagem externa. Commits locais registrados
em [progresso](progress.md); sem push. CI configurada, ainda não executada no GitHub.
Avisos conhecidos de teste: depreciações Starlette/httpx e AnyIO, não suprimidas.

# P2 — Inteligência de vagas com IA

Implementação local autorizada em 2026-09-20. Um commit por etapa; nenhum push.

| Etapa | Escopo | Estado |
|---|---|---|
| P2-01 | OpenAI, segredo privado e contratos | Implementado |
| P2-02 | Reservas atômicas, custos, limites e tracing | Implementado |
| P2-03 | Parser com saída estruturada e citações verificadas | Implementado |
| P2-04 | Normalização, confiança e revisão na interface | Implementado |
| P2-05 | Embeddings e busca semântica | Implementado |
| P2-06 | Possíveis duplicados por similaridade | Implementado |
| P2-07 | Sugestões de matching com evidências | Implementado |
| P2-08 | Benchmark, segurança, E2E e documentação | Concluído; benchmark e aceitação real executados |

Consultar `git log --oneline --grep=P2-` para os commits correspondentes.

Commits: P2-01 `4b8b424`, P2-02 `5eb0363`, P2-03 `1a177d9`, P2-04 `e403608`,
P2-05 `f2716cc`, P2-06 `831a780`, P2-07 `cb1f95d`. P2-08 é identificado pelo comando acima.
Veja [validação](validation.md) e [operação](operations.md). A chave real permanece fora do Git.

Fechamento após crédito de US$10: commit `2721c91` corrige parsing/normalização e matching a
partir dos testes reais. O commit de encerramento reúne relatórios, seleção e documentação;
consulte `git log --oneline --grep=P2`. Total contabilizado €0,13299404 (aprox. US$0,1064),
sem reservas pendentes. 57 testes de API, 11 componentes e 4 E2E aprovados.

## Fontes verificadas em 2026-09-20

- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs): Responses com JSON Schema estrito; validação local continua obrigatória.
- [GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini): US$0,40 entrada e US$1,60 saída por milhão de tokens.
- [GPT-4.1 nano](https://developers.openai.com/api/docs/models/gpt-4.1-nano): US$0,10 entrada e US$0,40 saída por milhão.
- [Embeddings](https://developers.openai.com/api/docs/models/text-embedding-3-small): US$0,02 por milhão de tokens.
- [Dados na API](https://developers.openai.com/api/docs/guides/your-data): `store=false` evita armazenamento de estado da resposta; não equivale a Zero Data Retention. Logs de monitorização de abuso podem reter conteúdo até 30 dias. Não presumimos residência europeia configurada nesta conta.

Um único provedor explicitamente escolhido pelo utilizador. Sem ferramentas ou fallback.
Mini/nano foram comparados nos 20 casos: mini 20/20 válidos, nano 18/20. Mini escolhido para
uso assistido local; nano também perdeu uma condição de sponsorship na revisão documental.
Precisão dos quatro campos básicos não representa precisão de todos os requisitos ou matching.
Preço local versionado expira em 30 dias. Conversão contábil conservadora de €1,25/US$,
não cotação cambial. Reservas e totais são do projeto, não de outras aplicações na conta.

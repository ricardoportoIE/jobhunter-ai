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
| P2-07 | Sugestões de matching com evidências | Pendente |
| P2-08 | Benchmark, segurança, E2E e documentação | Pendente |

Consultar `git log --oneline --grep=P2-` para os commits correspondentes.

## Fontes verificadas em 2026-09-20

- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs): Responses com JSON Schema estrito; validação local continua obrigatória.
- [GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini): US$0,40 entrada e US$1,60 saída por milhão de tokens.
- [GPT-4.1 nano](https://developers.openai.com/api/docs/models/gpt-4.1-nano): US$0,10 entrada e US$0,40 saída por milhão.
- [Embeddings](https://developers.openai.com/api/docs/models/text-embedding-3-small): US$0,02 por milhão de tokens.
- [Dados na API](https://developers.openai.com/api/docs/guides/your-data): `store=false` evita armazenamento de estado da resposta; não equivale a Zero Data Retention. Logs de monitorização de abuso podem reter conteúdo até 30 dias. Não presumimos residência europeia configurada nesta conta.

Um único provedor explicitamente escolhido pelo utilizador. Sem ferramentas ou fallback.
Os modelos mini/nano serão comparados no dataset público antes da escolha final.
Preço local versionado expira em 30 dias. Conversão contábil conservadora de €1,25/US$,
não cotação cambial. Reservas e totais são do projeto, não de outras aplicações na conta.

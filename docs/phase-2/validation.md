# Validação de P2 — 2026-09-20

P2-01 a P2-07 implementados. P2-08 entrega testes, integração local, benchmark reproduzível
e documentação. **A aceitação empírica da IA permanece pendente:** após duas respostas HTTP 429,
o utilizador confirmou que o faturamento da API ainda não está configurado. Nenhuma nova
chamada externa foi feita depois disso. A chave não foi exibida.

| Verificação | Resultado |
|---|---|
| Python/API/PostgreSQL | 56 aprovados (suite de 55 + teste adicional de recuperação/retry) |
| Componentes React | 11 aprovados |
| Playwright desktop/mobile | 4 fluxos completos aprovados |
| Ruff, formatação e mypy estrito | Aprovados |
| ESLint, Prettier, TypeScript, Vite e wheel | Aprovados |
| Compose, migrations e runtime restrito | Serviços saudáveis |
| Smoke e autenticação no proxy de produção | Aprovados; status/índice/histórico de IA acessíveis |
| Segredo em arquivos versionáveis, histórico Git e assets web | Não encontrado |
| Screenshots de extração/busca | Inspeção visual desktop/mobile, sem overflow |
| Contrato de benchmark P2 | Validado offline; nenhuma métrica de IA fabricada |

IA foi testada com respostas sintéticas e transportes simulados. E2E isola os dados em
`jobhunter_test_e2e`, remove a chave real e substitui o provedor somente no servidor de testes.
Produção usa o adapter OpenAI real. Esses testes não estabelecem qualidade/latência/custo real.

Cobertura: autenticação, CSRF, ownership, citações inventadas, schema inválido, recusas,
saídas incompletas, ausência de ferramentas, injeção tratada como dado, reservas concorrentes,
retries/cache, limite combinado, preços vencidos, timeout, virada do mês, reconciliação,
eliminação durante inferência, embeddings versionados, duplicados entre cidades, consentimento,
evidências selecionadas e score somente após revisão. O fluxo manual do P1 continua coberto.

## Pendência externa

As duas tentativas utilizaram um anúncio **fictício** com GPT-4.1 mini. Ambas retornaram 429,
sem tokens informados; consumo contabilizado local: €0. Isso não é consulta/comprovação da
fatura. Nenhum CV ou fato real do candidato foi enviado. Nano e embeddings não foram chamados.

O [relatório](../../data/evals/phase2-benchmark.json) registra `not_run_billing_required`, sem
métricas ou vencedor. O runner separa development/holdout, não envia rótulos esperados e
registra recusas, tokens, saídas inválidas, custo e p50/p95. Mini é padrão provisório.
Após ativar faturamento, executar [o benchmark](operations.md), revisar divergências e registrar
a seleção. O dataset público não permite concluir precisão de matching pessoal.

CI atualizada para testes e benchmark offline, ainda sem execução no GitHub e sem push.
Avisos de teste conhecidos: Starlette/httpx e alias AnyIO descontinuados, não suprimidos.

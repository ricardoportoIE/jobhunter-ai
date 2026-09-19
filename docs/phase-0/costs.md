# Orçamento final da fase 0

Definido em 2026-09-19: **€25 por mês combinado, até €15 AWS e €10 inferência**. Esses limites incluem margem para impostos, câmbio, retries e cobrança residual. Nenhum serviço pago foi ativado.

## Baseline que cabe no orçamento

| Etapa | AWS | Inferência | Condição |
|---|---:|---:|---|
| Fase 1 local | €0 | €0 | Sem recursos cloud ou LLM |
| Fases 2–3 locais | €0 por padrão | Até €10/mês | Benchmark e ledger de consumo antes de chamadas |
| Sessões de validação AWS | Reserva de até €5/sessão, duas sessões/mês | Dentro dos mesmos €10 | Cotação aprovada pelo preflight e TTL de no máximo 8h |
| Resíduos, logs, armazenamento e margem AWS | Reserva €5/mês | — | Soma AWS nunca autoriza mais de €15 |

Reservas são limites de autorização do projeto, não preços garantidos para a topologia. Não existe AWS 24/7 no baseline. Se a cotação regional exceder a reserva, reduzir o ambiente ou usar somente local. Ver [ADR-004](../adr/0004-local-first-budget.md).

## Estimativa de inferência

Volume de referência: 300 análises/mês com 4.000 tokens de entrada e 1.000 de saída por análise; 30 pacotes com 10.000 de entrada e 3.000 de saída por pacote. Total 1,5 milhão de entrada e 0,39 milhão de saída, contando todas as chamadas dentro de cada tarefa.

Com a tarifa de referência consultada para Haiku 4.5 via API direta, US$1/M de entrada e US$5/M de saída, o cálculo é `1,5 × 1 + 0,39 × 5 = US$3,45`. Acrescentar 30% de retries/validação resulta em US$4,49. É um cenário, não escolha de provider; não inclui pesquisa web paga ou contexto adicional. [Tarifa oficial](https://platform.claude.com/docs/en/about-claude/pricing).

Para reservar orçamento, usar provisoriamente a paridade conservadora US$1=€1 como **parâmetro de planejamento, não cotação cambial**, mais 30% de margem fiscal/cambial: aproximadamente €5,84. Substituir por câmbio e impostos efetivos no preflight. Cobrança real e reservas prevalecem sobre essa aproximação. O limite de €10 não autoriza número ilimitado de chamadas de agentes.

## Estimativa AWS temporária

Cenário: até 8h de um banco pequeno Single-AZ, API e rede temporárias; tarefas episódicas de documentos; volume baixo de logs e armazenamento. Para planejamento, reservar €0,40/h de computação+rede, €0,80 de armazenamento/requests/resíduos da sessão e 25% de contingência: `(8 × 0,40 + 0,80) × 1,25 = €5`. A taxa agregada é uma hipótese conservadora a validar, não preço regional cotado. Duas sessões reservam €10, restando €5 para custos AWS adicionais.

Antes de qualquer apply, exportar cotação por SKU em eu-west-1: RDS+storage/backups, Fargate/Lambda, rede/NAT ou endpoints, endereços IP, eventual ALB, logs, Secrets Manager, S3, ECR e transferência. A topologia completa poderá exceder €5 e deve então ser reduzida. Não depender de free tier, créditos ou assinatura de chat.

RDS parado ainda cobra armazenamento; NAT e outros recursos provisionados cobram enquanto existem. Destruir apenas compute não prova encerramento de gastos. Referências: [RDS](https://aws.amazon.com/rds/postgresql/pricing/), [VPC](https://aws.amazon.com/vpc/pricing/), [Fargate](https://aws.amazon.com/fargate/pricing/), [Lambda](https://aws.amazon.com/lambda/pricing/). Preços regionais serão revalidados no momento do deploy.

## Política de interrupção

Alertas em 50/80/100%: combinado €12,50/€20/€25, AWS €7,50/€12/€15 e IA €5/€8/€10. Antes de uma operação, verificar `gasto confirmado + reservas em aberto + custo máximo previsto`. Bloquear se superar qualquer limite aplicável. Falta de dados confiáveis bloqueia novas despesas; revisões manuais não reiniciam o contador automaticamente.

Alarme de billing pode chegar atrasado e não desliga recursos existentes. O design exige reservas atômicas, limites de tokens/chamadas, TTL, teardown e conferência de resíduos. Ao atingir €25, bloquear novas implantações e inferências pagas; continuar permitindo exportação e ações que parem custos. As proteções ainda precisam ser implementadas nas fases correspondentes.

Depois de cada sessão: guardar evidências técnicas anonimizadas, exportar dados necessários, destruir o workspace Terraform correto, verificar RDS/ECS/NAT/ALB/IPs/endpoints/snapshots e atualizar o ledger. Estado canônico pessoal permanece local.

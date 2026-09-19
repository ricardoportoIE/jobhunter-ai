# ADR-004 — Desenvolvimento local e AWS temporária

Estado: adotado para a fase 1 com base nas preferências fornecidas. Data: 2026-09-19.

O orçamento combinado é €25/mês: até €15 AWS e €10 inferência. A topologia de produção permanente descrita inicialmente não cabe com segurança nesse limite. O produto será utilizado localmente; AWS servirá inicialmente para demonstrações e validações temporárias reproduzíveis.

## Decisão

Fase 1 sem serviços cloud ou LLM. Fases 2–3 usam inferência somente dentro do orçamento. Fase 5 cria ambientes temporários, captura evidência técnica anonimizada, exporta dados necessários e destrói recursos do projeto com Terraform após a sessão. RDS, ECS, NAT Gateway e ALB não permanecem ativos por padrão. Nunca destruir recursos alheios ao workspace/estado Terraform selecionado.

Planejar até duas sessões mensais de oito horas, com reserva máxima inicial de €5 por sessão AWS e €5 para armazenamento, logs, resíduos e contingências do mês. O preflight deve usar a cotação vigente de todos os recursos; se uma sessão não couber na reserva, reduzir a topologia ou não implantar. O limite de tempo é um mecanismo de controle, não uma garantia do preço.

Alertas em 50%, 80% e 100% para cada suborçamento e para o combinado. Bloquear novas chamadas pagas e novos applies quando custo confirmado + reservas + custo máximo estimado ultrapassar um limite. Gastos desconhecidos ou informação de billing desatualizada impedem nova alocação. Destruição, exportação e ações necessárias para encerrar recursos continuam permitidas mesmo após o limite.

AWS Budgets pode avisar com atraso e recursos existentes continuam cobrando. A proteção exige preflight, reserva atômica, TTL e cleanup verificável; não prometer um hard cap de fatura oferecido pela AWS. Não há infraestrutura nem bloqueio operacional implementados nesta fase.

## Consequências

Não existe serviço disponível 24/7 na AWS no baseline. Dados pessoais e estado canônico permanecem locais; demos cloud usam seed fictício sempre que possível. A demonstração de portfólio registra infraestrutura realmente validada e depois removida, sem anunciar URL permanente. Um deploy contínuo exigirá novo orçamento e ADR.

# Fontes selecionadas e regras de acesso

Pesquisa em 2026-09-19. Canal inicial: texto fornecido pelo utilizador, com URL apenas como proveniência. Primeiro piloto automático futuro: Greenhouse Job Board API, começando por um board pequeno e relevante (`fosphamarketing`). Gmail é o primeiro provider de email; OAuth e leitura de label dedicada entram somente na fase 4. Nenhuma caixa de email foi acessada nesta fase.

## Registro de fontes

| Fonte | Escopo atual | Decisão |
|---|---|---|
| Texto manual | Importação local autorizada pelo utilizador | Selecionado para fase 1 |
| Greenhouse público | GET de anúncios selecionados para pesquisa e avaliação | Pesquisa pontual realizada; scheduler/conector ainda desligado |
| Greenhouse piloto Fospha | Um board, leitura e deduplicação | Selecionado; nova revisão de termos por finalidade antes de habilitar polling |
| Gmail | Label dedicada a alertas; sem envio nem alteração | Selecionado para fase 4, não conectado |
| Lever | Alternativa posterior | Não implementado |
| LinkedIn automatizado | Login, scraping e candidatura | Bloqueado |

A documentação oficial declara GET público sem autenticação e separa submissão autenticada. A consulta pontual usou apenas endpoints documentados. Acesso técnico público não equivale a licença ampla para redistribuir conteúdo. Usar apenas fatos derivados/reformulados no repositório e preservar originais privados. [Greenhouse Job Board API](https://docs.greenhouse.io/job-board.html).

Referências e decisões detalhadas por snapshot estão no registro privado. A URL genérica de termos consultada não respondeu; isso foi registrado e não foi tratado como permissão para polling contínuo. Antes da fase 4, confirmar os termos aplicáveis de plataforma/empregador, finalidade, retenção e frequência. Se não houver base suficiente, manter importação manual e não habilitar o board.

## Contrato do conector futuro

ID, domínio/board, endpoints, finalidade, URLs dos termos, data/responsável da revisão, decisão, limites e próxima revisão. Somente `ENABLED` permite execução agendada. GET com concorrência 1, cache, polling diário inicial, timeout 15s, até 2 retries transitórios e respeito a Retry-After. Parar em 401/403 e nunca contornar CAPTCHA. Revalidar DNS/IP e redirects contra SSRF. Email não autoriza seguir automaticamente os links incluídos.

## Dataset entregue

Vinte anúncios reais selecionados de endpoints oficiais, com 12 registros para desenvolvimento e 8 para avaliação. [Dados derivados](../../data/evals/real-cases.json) e [relatório](evaluation-report.md). Os originais, hashes, timestamps e URLs estão em `.private/evaluation/`. A análise inclui um caso fora do mercado-alvo, uma duplicata confirmada e um conflito real entre título e descrição.

Rótulos feitos pelo assistente são expectativas de design, não gold labels humanos. A avaliação de concordância humana, precisão e calibração será registrada quando o fluxo de matching for implementado. O dataset sintético continua separado e não foi contado como vaga real.

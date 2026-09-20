# ADR-002 — Inferência e execução de agentes

Estado: adotado para uso local assistido. Modelo selecionado no benchmark P2 em 2026-09-20.

Atualização P2, 2026-09-20: o utilizador escolheu OpenAI e forneceu chave privada. Adapter
Responses/embeddings implementado com orçamento local e revisão humana. Após o crédito de
US$10, o benchmark real foi executado. GPT-4.1 mini escolhido: 20/20 saídas válidas e 79/80
campos básicos corretos. Nano: 18/20 válidas e perda de condição de sponsorship na revisão.
O custo de mini nos 20 casos foi €0,02443300; seleção para rascunhos revisados, sem alegar
precisão de matching pessoal ou gold humano. [Evidências e limites](../phase-2/validation.md).
Ver [operação P2](../phase-2/operations.md).

## Distinção necessária

Bedrock oferece acesso a modelos; AgentCore oferece capacidades de execução e ferramentas para agentes. Um não é requisito automático do outro. LangGraph é uma biblioteca de orquestração com persistência e interrupções para revisão humana. [AgentCore](https://aws.amazon.com/bedrock/agentcore/pricing/), [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview).

## Comparação

| Caminho | Valor para o projeto | Trade-off | Posição |
|---|---|---|---|
| Regras Python sem LLM | Resultado testável, sem inferência paga | Requisitos precisam ser estruturados manualmente | Fase 1 |
| Bedrock + código próprio em Lambda/Fargate | Integração com a arquitetura AWS e controle de adapters | Seleção regional/modelo, quotas e rede a validar | Preferência para piloto cloud |
| API direta de modelo, como Anthropic | Menos infraestrutura para experimentar localmente | Segredo e política de dados de outro provider; inferência continua paga | Alternativa para benchmark |
| Bedrock + AgentCore Runtime | Execução gerida e componentes de agentes reutilizáveis | Superfície operacional e cobrança adicionais ao modelo | Adiar até existir requisito demonstrável |
| Modelo local | Controle do ambiente e ausência de cobrança por chamada externa | Hardware, manutenção, latência e qualidade precisam de benchmark | Opcional, fora do baseline |

AgentCore possui cobrança própria por consumo, separada da inferência. A API direta também cobra por tokens; não presumir uso coberto por uma assinatura de chat. [AgentCore pricing](https://aws.amazon.com/bedrock/agentcore/pricing/), [Claude API pricing](https://platform.claude.com/docs/en/about-claude/pricing).

## Decisão proposta

Na fase 2, criar porta `StructuredInference` com schema de entrada/saída, versão de modelo/prompt, timeout e contabilização de tokens. Um adapter inicial basta. Sem fallback silencioso que envie dados para outro provider. O dataset real inicial já está preparado; a seleção definitiva requer benchmark e revisão de residência/retenção de dados e disponibilidade na região alvo. O teto de inferência é €10/mês, dentro de €25 combinados; ver ADR-004.

Bedrock é candidato preferido para a AWS; API direta é alternativa de desenvolvimento. AgentCore não entra no MVP por padrão. LangGraph só entra quando houver workflow que precise de checkpoint, retomada e revisão; extração simples pode ser uma chamada estruturada. A documentação descreve esses recursos, mas nossa persistência e recuperação precisarão de testes próprios. [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview).

## Como decidir por evidência

Executar os mesmos 20 casos com dois candidatos, registrar precisão de campos, recusas, saída inválida, latência p50/p95 e custo completo incluindo retries. Escolher o modelo mais barato que cumpra os gates de qualidade e privacidade. Comparação executada em P2: mini passa os gates; nano não. Novos casos com revisão humana são necessários para estimar generalização e calibração.

Reavaliar AgentCore quando isolamento de browser, identidade de ferramentas ou gestão de sessões resolverem uma necessidade medida que Lambda/Fargate não atendam com simplicidade. MCP entra apenas quando ferramentas forem reutilizadas por clientes distintos.

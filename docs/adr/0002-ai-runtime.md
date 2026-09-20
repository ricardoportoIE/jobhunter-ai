# ADR-002 — Inference and agent execution

Status: adopted for assisted local use. Model selected in the P2 benchmark on 2026-09-20.

P2 update, 2026-09-20: the user selected OpenAI and supplied a private key. The
Responses/embeddings adapter was implemented with local budgeting and human review. After
US$10 was credited, the live benchmark ran. GPT-4.1 mini was selected: 20/20 valid outputs
and 79/80 correct basic fields. Nano: 18/20 valid outputs and a sponsorship condition lost
in review. Mini cost €0.02443300 for the 20 cases; it was selected for reviewed drafts,
without claiming personal matching accuracy or human gold-standard labels.
[Evidence and limitations](../phase-2/validation.md). See [P2 operations](../phase-2/operations.md).

## Necessary distinctions

Bedrock provides access to models; AgentCore provides execution capabilities and tools for agents. Neither automatically requires the other. LangGraph is an orchestration library with persistence and interrupts for human review. [AgentCore](https://aws.amazon.com/bedrock/agentcore/pricing/), [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview).

## Comparison

| Approach | Value to the project | Trade-off | Position |
|---|---|---|---|
| Python rules without an LLM | Testable results without paid inference | Requirements must be structured manually | Phase 1 |
| Bedrock + custom code in Lambda/Fargate | Integration with the AWS architecture and control over adapters | Regional/model selection, quotas and networking require validation | Preferred for the cloud pilot |
| Direct model API, such as Anthropic | Less infrastructure for local experiments | Another provider's secret and data policy; inference remains chargeable | Benchmark alternative |
| Bedrock + AgentCore Runtime | Managed execution and reusable agent components | Additional operational surface and charges beyond model inference | Defer until there is a demonstrable requirement |
| Local model | Control over the environment and no external per-call charges | Hardware, maintenance, latency and quality require benchmarking | Optional, outside the baseline |

AgentCore has its own usage charges, separate from inference. Direct APIs also charge for tokens; do not assume a chat subscription covers usage. [AgentCore pricing](https://aws.amazon.com/bedrock/agentcore/pricing/), [Claude API pricing](https://platform.claude.com/docs/en/about-claude/pricing).

## Proposed decision

In phase 2, create a `StructuredInference` port with input/output schemas, model/prompt versions, a timeout and token accounting. One initial adapter is sufficient. No silent fallback that sends data to another provider. The initial real-world dataset is ready; final selection requires a benchmark and a review of data residency/retention and availability in the target region. The inference ceiling is €10/month within the combined €25 budget; see ADR-004.

Bedrock is the preferred AWS candidate; a direct API is a development alternative. AgentCore is not included in the MVP by default. Introduce LangGraph only when a workflow needs checkpoints, resumption and review; simple extraction may require just one structured call. Its documentation describes these capabilities, but our persistence and recovery require their own tests. [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview).

## Evidence-based selection

Run the same 20 cases with two candidates and record field accuracy, refusals, invalid outputs, p50/p95 latency and full cost including retries. Select the cheapest model that passes the quality and privacy gates. The P2 comparison was completed: mini passes the gates; nano does not. New cases with human review are needed to estimate generalisation and calibration.

Reassess AgentCore when browser isolation, tool identity or session management addresses a measured need that Lambda/Fargate cannot meet simply. Introduce MCP only when distinct clients reuse tools.

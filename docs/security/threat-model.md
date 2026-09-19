# Threat model inicial

Estado: controles locais da fase 1 implementados e testados; controles de IA, conectores, renderer e cloud seguem nas fases correspondentes. Ver [segurança e dados de runtime](../phase-1/security-and-data.md). Responsável inicial por validação: mantenedor do projeto. Dados reais permanecem separados em `.private/`; só exemplos fictícios e dados derivados sem contatos são versionáveis. Ver [fronteiras de confiança](../architecture/overview.md).

Ativos: perfil factual, dados pessoais, documentos, credenciais de fontes/providers, aprovações, histórico e orçamento. Atacantes possíveis: fonte maliciosa, arquivo submetido, sessão não autorizada ou dependência comprometida.

| ID / prioridade | Ameaça e impacto | Controle planejado | Verificação e fase |
|---|---|---|---|
| T01 / P0 | Vaga injeta instruções para roubar perfil ou chamar ferramentas | Conteúdo delimitado como dado; ferramentas mínimas; política de autorização fora do LLM; schema estrito | Fixture malicioso não pode executar ferramenta; fase 2 |
| T02 / P0 | URL/redirect acessa metadata, localhost ou rede privada | Allowlist, HTTPS, resolução DNS validada e fixada na conexão, bloquear endereços não públicos IPv4/IPv6, revalidar redirects, limites de bytes/tempo | Testar metadata, IPv6, DNS rebinding e redirects; antes de fetch |
| T03 / P0 | Usuário não autorizado lê CV ou aprova candidatura | Sessão autenticada, ownership em cada recurso, CSRF quando cookie, expiração e invalidação | API sem sessão/ator correto retorna 401/403; fase 1 |
| T04 / P0 | LLM inventa experiência ou usa fato vencido | Fatos verificados por uso/validade; validator fora do gerador; evidence coverage obrigatório | Skill sem evidência ou revogada bloqueia pacote; fase 3 |
| T05 / P0 | Replay ou aprovação antiga envia versão errada | Hash, versões, escopo, expiração, lock e idempotência; reconciliar resultado ambíguo | Repetir decisão e simular timeout após envio; fases 3/6 |
| T06 / P0 | CV/anexo malicioso compromete renderer | Extensão e assinatura verificadas, limites de expansão/tamanho, sem macros, renderer isolado sem rede e com filesystem temporário | ZIP bomb, macro, path traversal e limite de CPU; antes de upload |
| T07 / P0 | PII/segredos vazam por Git, logs ou prompts | Dados privados separados, redaction, secret scanning, contexto mínimo, revisão de provider | Capturar logs de falha e diff de fixture; fases 1/2 |
| T08 / P1 | Workers e browser têm permissões excessivas | IAM por tarefa, allowlist de ferramentas/destinos, rede isolada, tokens curtos | Tentativa de recurso fora do escopo deve falhar; fases 5/6 |
| T09 / P1 | Histórico é alterado e perde valor de auditoria | Papel de aplicação sem update/delete em eventos, evento na transação; export de integridade | Testar rollback e permissão SQL; fases 1/5 |
| T10 / P0 | Loop de agente ou polling gera custos inesperados | Limite de chamadas/tokens/tempo, ledger com reserva atômica de orçamento, retries limitados | Duas tarefas concorrentes não ultrapassam saldo reservado; fase 2 |
| T11 / P1 | Dependência comprometida ou vulnerável | Lockfiles, análise de dependências/segredos, CI com permissões mínimas, atualizações revisadas | Verificação em PR; antes do uso de cada dependência |
| T12 / P1 | Perda ou restauração indevida de dados pessoais | Backup privado, recuperação ensaiada, reaplicar eliminações, lifecycle | Restore em ambiente isolado com dados de teste; fase 5 |
| T13 / P0 | Texto externo vira HTML/script no browser | Escape por padrão, sem HTML bruto; sanitização se necessária; CSP no deploy | XSS em título/descrição/evidência não executa; fase 1 |

## Retenção, logging e aprovação

Logs guardam IDs de correlação, duração, contagens, códigos de erro e custos, sem corpos completos de perfil, prompt ou CV. Registrar decisões resumidas e evidências, sem raciocínio interno do modelo. Auditoria append-only é um controle contra o papel da aplicação; não prometer imutabilidade absoluta perante administradores.

Política de retenção proposta em [Candidate Knowledge Base](../phase-0/candidate-knowledge-base.md). Criptografia em trânsito e em repouso no deploy. Revisar envio e retenção por modelo/provider, incluindo routing regional, antes de usar dados pessoais.

## Riscos residuais e resposta

Fact-checking automático pode falhar e evidência aprovada pode estar errada; manter revisão humana. Provider externo recebe o contexto autorizado: minimizar dados e permitir revogação de acesso. Fonte pode mudar termos: suspender conector até nova revisão. AWS é efêmera e o estado canônico fica local; exportação e recuperação precedem teardown. RPO 24h/RTO 8h são metas locais iniciais a demonstrar, não SLA garantido. Ao atingir orçamento, impedir novas despesas e permitir ações que encerrem custos existentes; alarmes isolados não garantem o teto.

Em suspeita de incidente: interromper workers/envios, revogar credenciais afetadas, preservar apenas evidências necessárias com acesso restrito, avaliar impacto, corrigir e registrar a retomada. Obrigações legais específicas exigem análise própria antes de lançamento público; este documento descreve controles técnicos de projeto.

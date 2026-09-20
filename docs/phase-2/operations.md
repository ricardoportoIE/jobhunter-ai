# Operação local de P2

## Estado e configuração

OpenAI foi escolhido pelo utilizador. A chave fornecida foi importada para `.env`, ignorado
pelo Git, sem ser exibida. Somente a API recebe a chave; ela não entra no frontend ou nas imagens.
As duas verificações iniciais receberam HTTP 429. Após o utilizador adicionar US$10 e autorizar
os testes, parsing, matching, embeddings e o fluxo HTTP real foram validados. Veja os
[resultados, consumo e limites da avaliação](validation.md).

Para configurar/substituir a chave, execute na raiz:

```powershell
python scripts/configure_openai.py C:\caminho\privado\openai-key.txt
docker compose up --detach --wait api
```

O importador aceita exatamente uma chave, não imprime seu valor e preserva as outras opções.
Use `docker compose config --quiet` para validar configuração sem imprimir segredos.
O arquivo original em Downloads foi preservado.

| Configuração em `.env` | Padrão / limite |
|---|---|
| `JOBHUNTER_OPENAI_API_KEY` | Segredo exclusivo do backend |
| `JOBHUNTER_AI_MODEL` | `gpt-4.1-mini-2025-04-14`, escolhido no benchmark para uso revisado |
| Modelos adicionais permitidos | `gpt-4.1-nano-2025-04-14`, `gpt-5.6-luna` |
| Matching / segunda avaliação | `JOBHUNTER_AI_MATCHING_MODEL` / `JOBHUNTER_AI_REVIEW_MODEL`: Luna high |
| Extração / estratégia | `JOBHUNTER_AI_PARSING_MODEL` / `JOBHUNTER_AI_STRATEGY_MODEL`: mini |
| Pesquisa pública | `JOBHUNTER_AI_RESEARCH_MODEL`: Luna high, até 3 buscas por chamada |
| Embeddings | `text-embedding-3-small`, 256 dimensões |
| `JOBHUNTER_AI_MONTHLY_EUR` | €10; pode reduzir |
| `JOBHUNTER_COMBINED_MONTHLY_EUR` | €25; reserva integral de €15 para AWS |
| `JOBHUNTER_AI_EUR_PER_USD` | 1,25: margem contábil, não cotação cambial |
| `JOBHUNTER_AI_PRICES_REVIEWED` | 2026-09-19 UTC / 2026-09-20 em Londres; expira em 30 dias |

Antes de atualizar a data de revisão, confira as fontes oficiais no [registro da fase](progress.md)
e ajuste `PRICES` se necessário. Cada execução preserva preço e margem utilizados.

## Fluxo na interface

1. **Importar vaga → Extrair com IA:** envia apenas o anúncio e apresenta campos/requisitos
   com citações literais e confiança declarada, ainda não calibrada.
2. **Preencher rascunho para revisão:** transfere os campos sem publicar. Corrija-os e confirme
   a revisão. Uma citação confirma a origem do texto, não a interpretação correta.
3. **Avaliar requisitos:** escolha até 20 fatos para enviar junto de seus trechos de evidência.
   Fatos sensíveis, revogados, expirados ou sem revisão/evidência válida são excluídos.
   Sem fatos selecionados, retorna desconhecidos sem chamar a API.
4. Confira as sugestões, preencha as avaliações e confirme-as para calcular. A IA não produz
   o score; o motor determinístico do P1 preserva os snapshots e o vínculo à sugestão.
5. **Busca semântica:** indexe um registro por vez, depois pesquise. Envia a afirmação de um
   fato ou o texto da vaga; a consulta também gera um vetor. Os vetores e a pesquisa ficam locais.
6. **Possíveis duplicados:** usa texto e vetores existentes, sem chamada externa. Confirmar
   arquiva a vaga atual e preserva a principal e os históricos. Local/empresa conflitantes
   precisam ser corrigidos primeiro. Similaridade nunca faz merge automático.
7. **Atividade de IA:** mostra estado, tokens, duração, custos, reservas e alertas de uso.

Não há chamadas de IA em segundo plano. URLs de anúncios são referências, sem fetch automático.
**Consultar informação pública atualizada** permite busca explícita nos domínios escolhidos,
com citações e conferência humana. **Solicitar segunda avaliação** preserva as divergências.
Configuração por tarefa, prompts e evidências em [migração Luna](../evals/luna-migration.md).
Nenhuma candidatura ou mensagem é enviada.

## Custos, repetição e recuperação

Reservas são confirmadas no PostgreSQL antes da chamada externa. Conteúdo/modelo/prompt/schema
identificam a operação. Repetir um sucesso reutiliza o resultado; concorrência da mesma entrada
é bloqueada. O SDK não repete chamadas automaticamente. Depois de corrigir a causa de uma falha,
use **Tentar novamente após corrigir a causa**. O limite é duas tentativas por conteúdo em 24h.

Timeout, falha de transporte, HTTP 408/5xx ou uso desconhecido mantêm a reserva. Execução
`running` com mais de cinco minutos também bloqueia novas alocações. Após conferir o uso no
provedor, reconcilie administrativamente, sem presumir custo zero:

```powershell
uv run --project apps/api --env-file .env python -m jobhunter_api.ai_admin ID_DA_EXECUCAO --confirmed-eur VALOR_CONFIRMADO --billing-checked
```

Respostas inválidas/recusas com tokens são contabilizadas. Reservas atravessam a virada do mês.
Os limites protegem esta aplicação, não outros usos da chave/conta, impostos ou alterações não
revisadas do preço. A reserva de €15 não cria AWS nem consulta seu faturamento. Totais locais
não são uma fatura. Eliminação de dados não reinicia o orçamento.

## Benchmark e testes reais opcionais

Na raiz, para executar os 20 casos públicos com os dois candidatos:

```powershell
uv run --project apps/api --env-file .env python scripts/evaluate_phase2.py --live --max-additional-eur 1
uv run --project apps/api --env-file .env python scripts/validate_phase2_live.py --live
```

Sem `--live`, não há chamadas. Limite adicional: €1, sempre dentro do teto mensal. Relatório:
`data/evals/phase2-benchmark.json`. Salva cada resultado, reusa sucessos, interrompe em bloqueios
e não promove modelo automaticamente. Para uma falha já corrigida, `--attempt 2` permite a
segunda tentativa dentro do limite diário. Nenhum documento privado participa desse dataset.

O segundo comando executa provas fictícias de parsing adversarial, salário, matching, embeddings
e cache, com até €0,25 adicionais dentro do teto mensal. Não altera o perfil do candidato.
Resultado: `data/evals/phase2-live-acceptance.json`. Chamadas já concluídas são reutilizadas.
Uma nova execução do benchmark substitui o relatório desse caminho por resultados sem revisão;
use `--output OUTRO_CAMINHO.json` para preservar o relatório final selecionado.

Gates técnicos: ≥95% de saídas válidas e ≥95% de campos básicos corretos; citações inexistentes
são rejeitadas. A revisão humana deve avaliar interpretação de requisitos, desconhecidos,
recusas, falsos duplicados e matching. Dados reformulados/pseudonimizados não são gold humano.
Esse benchmark de parsing não mede a precisão de matching do candidato.
Na execução final, mini passou os gates; nano falhou em validade e perdeu uma restrição de
sponsorship. O split original foi reutilizado nos ajustes e não representa holdout intocado.
Revisão documental pelo assistente está registrada; revisão humana continua obrigatória por
vaga antes do score. Não existe aprovação humana de gold set implícita nesses resultados.

## Privacidade e limites

- Responses utiliza `store=false`, sem fallback. Ferramentas são exclusivas da pesquisa pública
  explícita; extração, matching e estratégia não navegam. Isso não equivale a Zero Data
  Retention. Os [controles oficiais](https://developers.openai.com/api/docs/guides/your-data)
  descrevem possível retenção em logs de abuso por até 30 dias. Não presumimos residência europeia.
- Matching envia título/texto/requisitos da vaga, fatos escolhidos e trechos, sem nome de apresentação ou referências/caminhos
  de documentos. PDFs/DOCX não são enviados automaticamente. Sugestões e snapshots ficam locais.
- Exportação inclui execuções e índice. Eliminação administrativa remove textos, resultados,
  vetores e vínculos pessoais, preservando custos sem proprietário. Uma resposta em andamento
  não pode restaurar o resultado após eliminação. Arquivos e retenção do provedor são separados.
- Entrada estruturada limitada conservadoramente por bytes a 200.000 tokens. Mini: até 5.000
  tokens de saída; Luna: 8.000 por padrão, configurável até 16.000, incluindo raciocínio.
  Timeout de rede de 180s e Nginx de 240s. Pesquisa reserva entrada de 200.000 tokens e até
  três buscas; uso acima do limite exige reconciliação. Nenhum loop automático de agente.
- Embeddings usam trechos de 1.000 caracteres. Busca suporta 5.000 trechos atuais e até 10
  resultados, excluindo registros editados, arquivados, revogados ou sem evidência válida.
- Duplicados comparam até 500 vagas ativas e mostram 20 candidatos. Jaccard ≥0,65 ou cosseno
  ≥0,90 são limiares heurísticos ainda sem calibração real.
- Projetos/cursos não sustentam automaticamente experiência profissional. Estratégia de
  carreira permanece desconhecida nas sugestões automáticas.

## Testes sem cobrança

Na pasta `apps/api`:

```powershell
$env:JOBHUNTER_TEST_DB_NAME = 'jobhunter_test'
uv run --locked --env-file ../../.env pytest
uv run --locked mypy
uv run --locked ruff check . ../../scripts/evaluate_phase2.py ../../scripts/configure_openai.py
uv run --locked ruff check ../../scripts/validate_phase2_live.py
uv run --locked python ../../scripts/evaluate_phase2.py --check
```

Na pasta `apps/web`: `npm run lint`, `npm test`, `npm run build`, `npm run test:e2e`.
No Windows validado, defina `$env:PLAYWRIGHT_CHANNEL='msedge'` para E2E. Fixtures ficam apenas
em `apps/api/tests`, fora da imagem de produção, sem chave real e sem chamadas pagas.

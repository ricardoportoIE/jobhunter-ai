# P3 — Validação de entrega

Execução local em 2026-09-20. Dados de testes fictícios, separados do perfil pessoal.

## Testes automatizados

- API: 69 testes, incluindo permissões por uso, consentimento, seleção inválida,
  versionamento, aprovação separada de respostas sensíveis, idempotência e diffs.
- Segurança: isolamento por utilizador, autenticação, CSRF, rejeição de IDs estranhos,
  minimização do payload de IA e exportação/eliminação de pacotes e snapshots.
- Documentos: download bloqueado antes de aprovação, hash dos arquivos no ZIP,
  mesmos fatos no DOCX/PDF, metadados de autor vazios e fontes alteradas bloqueadas.
- Frontend: 11 testes React; TypeScript, ESLint, Prettier e build de produção.
- Browser: 6 fluxos Playwright, cobrindo P1, P2 e P3 em desktop/mobile. P3 percorre
  estratégia → aprovação → geração → resposta sensível → nova versão → diff →
  aprovação → download PDF. Sem transbordamento horizontal nos dois viewports.
- Ruff, mypy, contratos de avaliação e smoke checks da stack Docker local.

Os testes HTTP/browser usam um provider determinístico e bancos `jobhunter_test*`.
Os testes reais abaixo exercitam o serviço de estratégia e orçamento com a OpenAI;
não são uma execução completa do browser contra a API externa. O workflow CI inclui
os novos testes e a checagem offline do relatório; não foi executado remotamente.
Persistem os dois avisos de depreciação Starlette/httpx e AnyIO já registrados em P2.

## OpenAI real

Foram feitas seis chamadas reais: três casos com o prompt inicial e três com o
prompt final `application-strategy-1.1`, usando o GPT-4.1 mini configurado.
Casos: seleção normal, instrução maliciosa dentro do anúncio e lacunas de experiência
comercial/MSc. Cada chamada foi repetida via cache sem nova cobrança.

O primeiro resultado confundia relevância de um diploma com cobertura de uma exigência
de MSc na explicação. O prompt final explicita a diferença de qualificação e a
impossibilidade de substituir anos comerciais por um projeto pessoal. O caso final
aponta ambas as lacunas. As alegações dos documentos sempre vieram dos fatos canónicos.

Os três casos finais passaram: IDs válidos, alegações copiadas dos fatos, nenhuma
experiência inventada no documento, perguntas de salário/visto sem resposta automática,
aprovação bloqueada enquanto faltam respostas, renderização DOCX/PDF e cache válido.

| Execução | Custo estimado no ledger |
|---|---:|
| Baseline, prompt 1.0 | €0,00382700 |
| Final, prompt 1.1 | €0,00418800 |
| Total P3 | €0,00801500 |

Equivale a aproximadamente US$0,006412 pelas tarifas registradas, antes da margem
contabilística de 1,25 usada no ledger. Isso não é uma conversão cambial nem uma
consulta ao saldo da carteira. Relatórios públicos contêm somente dados sintéticos:
[baseline](../../data/evals/phase3-live-baseline.json) e
[final](../../data/evals/phase3-live.json). Não constituem benchmark com gold set humano
nem permitem afirmar precisão geral de estratégia ou equivalência de qualificações.

Reproduzir sem chamadas externas, na raiz:

```powershell
uv run --project apps/api python scripts/evaluate_phase3.py --check
```

Teste externo explícito, sujeito aos limites mensais e a uma reserva adicional máxima
de €0,25; resultados já existentes podem ser atendidos pelo cache:

```powershell
uv run --project apps/api --env-file .env python scripts/evaluate_phase3.py --live
```

## Verificação visual

CV e carta fictícios foram gerados em ambos os formatos. Os PDFs do ReportLab foram
renderizados em PNG e inspecionados. Os DOCX foram convertidos com o helper
`render_docx.py` da skill documents, em container QA isolado com LibreOffice e Poppler,
sem rede durante a conversão. Esse container não integra o runtime da aplicação.

As quatro amostras têm uma página cada, com título preto, margens consistentes,
texto legível e sem cortes/sobreposição. Foi removida a borda colorida herdada do
template Word nos estilos usados. Também foram inspecionadas as capturas do pacote
aprovado em desktop e mobile. Artefatos QA ficam em `.private/p3-qa/` e
`apps/web/test-results/`, ignorados pelo Git.

DOCX e PDF compartilham o conteúdo estruturado; fontes e paginação podem variar entre
renderizadores. A prévia HTML permite revisão de conteúdo, sem prometer paginação
idêntica ao arquivo final. A inspeção de amostras não substitui a revisão de cada
documento pessoal antes do envio.

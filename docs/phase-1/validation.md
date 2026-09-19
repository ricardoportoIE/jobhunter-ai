# Validação técnica final da fase 1

Executada localmente em 2026-09-20. Implementação em dez etapas com commits locais; sem publicação remota.

| Check | Resultado |
|---|---|
| API: Ruff + formatação + mypy estrito | Aprovados |
| API: testes unitários/integração PostgreSQL | 36 aprovados; nenhum skipped na execução completa |
| Web: ESLint + Prettier + TypeScript estrito | Aprovados |
| Web: Vitest/jsdom | 9 aprovados |
| Browser E2E: desktop 1440px + mobile emulado | 2 aprovados no Edge 153 headless |
| Builds | wheel/sdist Python, bundle Vite e imagens Docker aprovados |
| Compose com banco vazio | Migrations, papel restrito, três serviços saudáveis e smoke aprovados |
| Smoke HTTP | Assets, API direta/proxy, OpenAPI e readiness PostgreSQL aprovados |
| Recuperação de banco | Liveness 200 durante indisponibilidade; readiness 503 e retorno 200 sem reiniciar API/web |
| Contratos de design | Validador público da fase 0 aprovado |
| Dataset real derivado | 20 casos executados; resultados e divergências versionados |
| GitHub Actions | Schema YAML validado; cinco jobs preparados, execução remota não realizada |

O E2E percorre login por teclado → evidência revisada → fato verificado → publicação de perfil → importação → revisão de requisito → avaliação com fato → score/cobertura → abertura de evidência do snapshot → shortlist → registro confirmado de envio manual → exportação → logout. Verifica ausência de execução de script importado, erros JavaScript e overflow horizontal. O banco usado é `jobhunter_test_e2e`, com dados fictícios.

A inicialização do zero foi verificada em um projeto Compose separado, com portas e volume próprios, removido ao término. O volume pessoal foi preservado. Nos testes de API, falha injetada de auditoria comprovou rollback; UPDATE/DELETE/TRUNCATE de auditoria e alterações de snapshots foram negadas ao papel runtime.

## Limites conhecidos

- O download do Chromium Playwright expirou; foi usado o canal oficial do Edge já instalado. O workflow Linux está configurado para Chromium. Não houve execução remota desse workflow.
- Há dois avisos de depreciação upstream no cliente de testes Starlette/httpx e AnyIO. Permanecem visíveis; não são falhas de testes.
- O dataset público não é gold humano e não contém o perfil factual privado. Sua execução preservou controles conservadores, mas teve divergências que exigem revisão; [detalhes](evaluation-results.md).
- Não há importação automática do CV privado, parser semântico, geração de pacote, envio, provider de IA ou recursos cloud nesta fase.

Comandos reproduzíveis: [desenvolvimento local](../local-development.md). Fontes da automação de navegador: [Playwright webServer](https://playwright.dev/docs/test-webserver) e [CI](https://playwright.dev/docs/ci).

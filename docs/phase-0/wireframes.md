# Quatro telas para o primeiro fluxo

Wireframes de baixa fidelidade, sem aplicação implementada. Textos e números ilustrativos; nenhum dado real. Fluxo: Perfil → Inbox/importação → Detalhe/análise → Tracker. Overview será resumo na Inbox; revisão de documentos ganha tela própria na fase 3.

## 1. Perfil e evidências

```text
+------------------------------------------------------------------+
| JobHunter AI     Vagas | Perfil | Candidaturas                     |
| Perfil — versão 1                  [Nova revisão]                 |
| Cargos: [por preencher]  Mercados: [por confirmar]                 |
| Restrições privadas: incompletas    [Rever em privado]              |
|                                                                  |
| Fato                  Estado          Evidência       Ações       |
| Exemplo fictício      Não verificado  [Adicionar]     [Rever]      |
|                                                                  |
| [Adicionar fato]  [Adicionar fonte]  [Publicar versão revista]      |
| Só fatos verificados e vigentes sustentam candidaturas.           |
+------------------------------------------------------------------+
```

Estado vazio pede fatos e evidências, sem autoaprovação. O detalhe de evidência mostra origem, localização, validade e usos. Campos sensíveis não aparecem na listagem nem no resumo do perfil.

## 2. Inbox e importação

```text
+------------------------------------------------------------------+
| Vagas                              [Importar texto de vaga]       |
| [País] [Modalidade] [Score] [Estado] [Revisão necessária]           |
|                                                                  |
| Cargo / empresa fictícia     Score    Cobertura    Estado         |
| Junior Backend / Empresa A   68/100   50%          Rever dados     |
| Graduate / Empresa B         —        —           Rever campos    |
|                                                                  |
| Importar: [texto da descrição.................................]   |
| Origem/URL opcional: [........................................]   |
| [Guardar e rever campos]                                         |
+------------------------------------------------------------------+
```

A URL é proveniência; a fase 1 não a visita. Erros de validação são locais aos campos. Detectar duplicado apresenta o registro existente e opção de revisar a versão, sem criar outra candidatura silenciosamente.

## 3. Detalhe e análise

```text
+------------------------------------------------------------------+
| Junior Backend / Empresa A       [Rever requisitos] [Analisar]     |
| Fonte e data | Vaga v1 | Perfil v1 | Algoritmo 0.2                |
| Score 68/100  | Cobertura 50% | REVISÃO NECESSÁRIA                 |
| Dados insuficientes: autorização e modalidade não confirmadas.    |
|                                                                  |
| Categoria       Peso     Atendimento     Cobertura               |
| Skills          30%      80%             100%                    |
| Experiência     20%      50%             100%                    |
| Demais          50%      desconhecido    0%                      |
|                                                                  |
| Atendidos [evidência] | Parciais [evidência] | Gaps | Blockers      |
| [Ver descrição] [Guardar na shortlist] [Arquivar]                 |
+------------------------------------------------------------------+
```

Exemplo segue o ADR-003. Blockers têm texto, não dependem de cor. Mostrar desconhecido separado de não atendido. Se perfil mudar, marcar análise desatualizada e pedir nova execução.

O detalhe também mostra «Início do trabalho: requer revisão» e suas flags. Uma recomendação positiva pode coexistir com sponsorship desconhecido; não esconder a vaga nem apresentar autorização de início como confirmada.

## 4. Tracker

```text
+------------------------------------------------------------------+
| Candidaturas            [Estado] [Empresa] [Registrar envio manual]|
| Shortlist       | Enviadas        | Entrevistas     | Encerradas   |
| Empresa A       | Empresa B       |                 |             |
|                                                                  |
| Detalhe da candidatura                                           |
| Timeline: criada → anotação → envio manual confirmado             |
| Canal: [........]  Data: [........]  Comprovante: [........]       |
| [Confirmar registro manual]                                      |
+------------------------------------------------------------------+
```

Registrar envio manual atualiza histórico, não envia nada externamente. A futura tela de pacote mostrará CV, carta, diff, evidências e campos sensíveis; aprovação de pacote e confirmação final de envio serão ações distintas.

## Interação comum

Navegação por teclado, foco visível, labels explícitos, contraste adequado, mensagens de carregamento/vazio/erro e confirmação de sucesso. Em telas pequenas, cards/lista substituem tabelas e Kanban. Não habilitar ações que exijam snapshot válido quando faltam requisitos.

# P3 — Preparar e aprovar uma candidatura

Abra uma vaga revisada e escolha **4. Pacote de candidatura**. O perfil precisa
estar publicado, com nome preenchido; a vaga precisa de cargo e empresa.

1. Selecione fatos revisados, com evidências atuais e permissão para os documentos
   desejados: `cv`, `cover_letter` e/ou `application_form`. A permissão `matching`
   isolada não autoriza documentos. Fatos e evidências marcados como sensíveis
   não entram na seleção automática.
2. Informe até quatro linhas de contato e, opcionalmente, perguntas do formulário,
   uma por linha. Os contatos ficam no pacote local.
3. Prepare a estratégia. Com IA, confirme o envio dos fatos selecionados, conteúdo
   das evidências, requisitos da vaga e perguntas à OpenAI. O campo de contato,
   nome do perfil e caminhos das fontes não são enviados; o texto das evidências
   pode conter dados pessoais, por isso confira a seleção. Também há modo manual.
4. Revise relevância, lacunas e pontos para entrevista. Ajuste a seleção e a ordem
   dos fatos do CV e da carta; confirme a revisão e aprove a estratégia.
5. Gere o pacote. Confira textos e origem de cada alegação. Respostas sem evidência
   precisam ser preenchidas e declaradas verdadeiras por você. Salário, imigração,
   disponibilidade e outras perguntas sensíveis exigem revisão específica.
6. Salve alterações como nova versão e consulte o histórico e as diferenças.
   Confira o inglês e a apresentação; aprove a versão para habilitar os downloads.

Arquivos disponíveis: `cv.docx`, `cv.pdf`, `cover-letter.docx`, `cover-letter.pdf`,
`answers.json`, `package.json` e um ZIP com todos eles e um manifesto SHA-256.
Escolha os arquivos adequados antes de partilhar: os JSON e o ZIP incluem respostas
e referências de origem que podem não ser necessárias ao empregador.

## Como o conteúdo permanece verificável

A IA propõe a seleção de IDs e explica relevância/lacunas. Um validador determinístico
confere IDs, permissões, cobertura dos requisitos e perguntas. A geração copia
literalmente as alegações dos fatos aprovados, incluindo nomes, datas e cargos.
Uma validação posterior recompõe o conteúdo e compara sua igualdade, verifica
respostas pendentes e registra alertas. Não há segundo modelo emitindo um parecer
de veracidade sobre textos livres.

Os modelos de documento usam British English. Os fatos não são traduzidos nem
reescritos automaticamente: para mudar uma alegação, corrija e revise o fato na
base canónica, publique o perfil quando necessário e gere outra estratégia.
A carta usa abertura e encerramento fixos, com fatos selecionados; não inventa
pesquisa sobre a empresa ou motivação pessoal. O CV agrupa os fatos por categoria,
preservando a ordem escolhida dentro de cada grupo.

A aprovação registra utilizador, data, versão e hash do conteúdo. Alterar o pacote
revoga a aprovação; alterar ou expirar uma fonte bloqueia novas aprovações e
downloads daquele pacote. Estratégias e versões anteriores continuam disponíveis
para consulta. Aprovar não envia uma candidatura nem altera automaticamente o tracker.

## Privacidade, custos e operação

Os documentos são renderizados em memória pelo backend local com `python-docx`
e ReportLab. O runtime não depende de Word, LibreOffice ou conversores cloud.
Os JSON de download omitem o snapshot completo e os caminhos privados das evidências.
Snapshots, respostas e histórico entram na exportação e eliminação dos dados locais;
arquivos já baixados continuam sob seu controle.

As chamadas usam o modelo, cache, reservas de orçamento e ledger de P2, visíveis em
**Atividade de IA**. Mantêm-se os tetos de €10/mês de IA e €25 combinados, conforme
[operação e privacidade de P2](../phase-2/operations.md). O modo manual e a renderização
local não consomem API. A configuração padrão usa GPT-4.1 mini.

Os contratos HTTP estão no [OpenAPI local](http://127.0.0.1:5173/api/docs).
P3 usa `records` e `snapshots` existentes, sem nova migration. As rotas incluem
estratégia por vaga, aprovação de estratégia, geração, atualização/revisão de pacote,
histórico/diff e download autenticado com versão esperada.

Limites: a classificação de perguntas sensíveis é heurística; todas as respostas
continuam sujeitas à revisão humana. Respostas manuais são declarações do candidato,
sem comprovação independente. O layout é de coluna única, orientado a ATS, mas não
foi certificado em serviços ATS externos. Conteúdo extenso pode gerar várias páginas;
confira os arquivos baixados antes de enviar.

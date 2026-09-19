# Dataset inicial e revisão

Vinte anúncios reais foram lidos por GET na API pública Job Board do Greenhouse durante esta fase. A cópia versionável contém reformulações curtas e aliases de empregadores; originais, URLs, IDs externos, timestamps e SHA-256 ficam no manifesto privado `.private/evaluation/provenance.json`. Não foram coletados dados de candidatos nem enviados formulários.

O [dataset](../../data/evals/real-cases.json) contém 12 casos de desenvolvimento e 8 de avaliação. Rótulos foram elaborados pelo assistente após leitura documental: **não são um gold set validado por humanos nem resultados de execução do algoritmo**. Essa distinção permite terminar a preparação de dados na fase 0 e medir/calibrar na fase 1.

## Cobertura observada

| Casos | Comportamento que deve ser preservado |
|---|---|
| REAL-01/02 | Graduate com limite ambíguo de experiência; pedir interpretação em vez de converter experiência de outra carreira em anos de SWE |
| REAL-03/04 | Internship exige estudos em andamento; formação concluída não prova matrícula atual |
| REAL-05/06/07 | Experiência comercial explicitamente requerida; portfólio não vira emprego comercial |
| REAL-08/09/20 | Nível Staff/Senior excluído, mesmo com tecnologias compatíveis |
| REAL-10 | Junior aceita projetos pessoais; sponsorship ausente não bloqueia |
| REAL-11/13 | Mesma função em dois boards; duplicata entre fontes, com diferença de boilerplate |
| REAL-12 | Título software engineer e corpo data engineer; revisão obrigatória e possível duplicata |
| REAL-14 | Janela de graduação, início futuro e tecnologia sem evidência |
| REAL-15 | Vaga de múltiplos níveis e regras próprias de clearance; não excluir por uma palavra isolada |
| REAL-16 | Suporte B2B exigido não é comprovado automaticamente por suporte interno |
| REAL-17 | Sponsorship condicional e conflito de datas no anúncio |
| REAL-18 | MSc obrigatório; não equiparar postgraduate diploma a mestrado |
| REAL-19 | Controle negativo fora de IE/UK, nível senior e negativa de sponsorship |

São 8 anúncios localizados na Irlanda, 11 no Reino Unido e 1 fora dos mercados-alvo para controle negativo. Dez registros vêm do mesmo empregador; a amostra é intencional e pequena, não representativa do mercado. Ela não é uma shortlist recomendada para candidatura.

## Deduplicação e separação

Descrições semelhantes, duplicatas e conflitos ficam no mesmo split. O agrupamento inclui o bloco REAL-10/11/12/13, os pares de graduate e internship em diferentes cidades. Existe uma duplicata confirmada de função entre boards; a hipótese inicial de coletar dois pares confirmados não foi forçada. O segundo par encontrado apresenta conflito de conteúdo e serve como teste de revisão, não merge automático.

Uma URL encontrada em pesquisa devolveu 404 na API oficial e foi substituída por um anúncio acessível. Resultados de busca não provam que uma vaga continua aberta. Antes de uma candidatura real, reler prazo, conteúdo e disponibilidade.

## Publicação e validação

Não publicar anúncios integrais nem contatos pessoais presentes em boilerplate. Os textos públicos são reformulações analíticas limitadas. Pseudonimização reduz identificadores diretos, mas títulos e características ainda podem permitir reidentificação; não alegar anonimização irreversível.

Validar contagem, IDs, splits, grupos sem vazamento, flags, ausência de score fabricado e rastreabilidade local dos snapshots. A revisão humana de concordância e os baselines de precisão/tempo pertencem ao piloto funcional, ainda não executado.

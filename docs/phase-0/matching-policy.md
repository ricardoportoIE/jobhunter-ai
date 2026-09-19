# Política de matching v0.2

Definição final da fase 0, baseada nas preferências fornecidas e na revisão das vagas reais. O perfil e as restrições pessoais exatas ficam em `.private/`.

## Prioridade de procura

Backend graduate/junior em Python ou Java primeiro; software/full-stack em seguida; automação e IA aplicada depois. Cloud/platform são alternativas quando incluem programação ou automação. Data analyst/data engineer não são alvos principais. Procurar Irlanda antes do Reino Unido, privilegiando Dublin híbrido, Dublin presencial e remoto dentro da Irlanda. Demais cidades, salários e relocação são avaliados caso a caso: não há piso salarial nem raio máximo confirmado.

Full-time é o objetivo. Part-time pode ser ponte, sem substituir a prioridade. Senior, Lead, Principal, Staff, Manager, Head e Architect são excluídos quando descrevem o nível da vaga. Não aplicar esse filtro a menções incidentais como «colaborar com senior engineers» nem a vagas explicitamente abertas a vários níveis.

## Separar procura e início de trabalho

Um candidato pode perseguir uma oferta que exija nova autorização antes do início. Ausência de sponsorship no anúncio é `unknown`, não «indisponível». Necessidade de alteração futura da autorização, isoladamente, não é blocker da procura e não reduz automaticamente o score técnico.

O resultado passa a ter `employment_gate`: `READY_WITHIN_CONFIRMED_LIMITS`, `REVIEW_BEFORE_START` ou `BLOCKED`, além da recomendação e de flags. Uma vaga tecnicamente adequada pode receber `APPLY_AFTER_REVIEW` e `REVIEW_BEFORE_START` simultaneamente. Isso nunca autoriza começar a trabalhar nem responder «autorização irrestrita» em formulários.

Bloquear ou despriorizar fortemente quando há condição obrigatória explicitamente incompatível: sem sponsorship quando suporte do empregador é necessário, autorização permanente irrestrita não negociável, nível avançado, experiência comercial obrigatória não sustentada, ou local comprovadamente inviável. Uma inferência jurídica de «nenhuma rota possível» exige fatos suficientes e revisão humana; o LLM não decide sozinho.

Regras migratórias são temporais e específicas. A orientação oficial irlandesa distingue limites de horas por período; manter o limite conservador declarado até revisão, sem atualizar direitos automaticamente pelo calendário. A rota britânica Skilled Worker exige oferta e empregador aprovado, com condições próprias. Referências: [ISD para estudantes](https://www.irishimmigration.ie/coming-to-study-in-ireland/frequently-asked-questions-for-students/) e [GOV.UK Skilled Worker](https://www.gov.uk/skilled-worker-visa/your-job). Estas fontes orientam flags; não confirmam a elegibilidade individual.

## Regras factuais aprendidas na análise

- Experiência em outra carreira e suporte adicional não equivale a anos de emprego como software engineer.
- Formação de pós-graduação comparável a Post-Graduate Diploma não deve ser apresentada como MSc.
- Certificações, diplomas, premiações e métricas de teste preservam o tipo de evidência: declaração do candidato, documentação pública ou verificação independente.
- Projetos em desenvolvimento não contam como entregas concluídas; conhecimento conceitual de RAG/agentes não comprova experiência em produção.
- Dois anúncios com texto idêntico em cidades diferentes não são automaticamente a mesma oportunidade.
- Conflito entre título e corpo da vaga exige revisão; não resolver silenciosamente escolhendo o título.

## Critérios de aceitação

Uma vaga junior full-time com boa aderência técnica e sponsorship desconhecido continua visível/recomendável com revisão. Negativa explícita de sponsorship preserva motivo. Salário ausente continua null. Requisito obrigatório de experiência comercial não é satisfeito por somar anos de outra profissão. Mudanças no perfil ou anúncio invalidam análises antigas. Ver [dataset real](../../data/evals/real-cases.json).

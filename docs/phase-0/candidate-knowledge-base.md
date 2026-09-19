# Master CV e Candidate Knowledge Base

## Separação entre template e dados reais

`data/templates/candidate-profile.json` é um formulário vazio validável. Copiar para `.private/candidate-profile.json` e preencher apenas com informações revistas. `.gitignore` reduz publicação acidental; não criptografa arquivos nem substitui controle de acesso. Usar armazenamento local protegido e verificar o diff antes de qualquer commit.

O master CV permanece privado em `.private/master-cv/`. Evidências privadas ficam em `.private/evidence/`. O DOCX e o PDF fornecidos foram lidos e comparados: 60 parágrafos correspondem após normalização textual; o PDF de duas páginas foi inspecionado visualmente. Originais preservados com SHA-256. O caminho antigo `data/cv/` indicado no material não existe e não foi criado para dados pessoais.

Base consolidada: 114 fatos, 43 evidências e quatro referências de repositórios fixadas por commit. O utilizador confirmou nesta conversa que fatos e datas do CV estão atuais. `verified` representa essa declaração aprovada, com documentação pública complementar quando disponível; nenhum teste dos projetos foi reexecutado. Qualificações e premiações mantêm origem declarativa até eventual comprovação documental, sem transformar diploma de pós-graduação em mestrado.

Arquivos privados: `candidate-profile.json`, `candidate-facts.json`, `candidate-evidence.json`, `candidate-fact-annotations.json`, `candidate-constraints.json` e `candidate-contact.json`. Contatos e restrições sensíveis ficam separados. Dados pessoais desnecessários continuam null. Projeto em desenvolvimento não é fato de entrega concluída.

## Processo de consolidação

1. Registrar versão, data e hash do CV original, mantendo uma cópia sem alterações.
2. Extrair fatos atômicos: uma experiência, competência, certificação ou realização por registro.
3. Associar evidência e localização exata: página, seção, arquivo/commit ou declaração aprovada do candidato.
4. Manter os fatos extraídos como `unverified` até revisão. CV é fonte declarativa, não confirmação independente.
5. Definir validade, usos permitidos e classificação de sensibilidade.
6. Revisar contradições, datas e métricas com o candidato; nunca escolher uma versão silenciosamente.
7. Publicar um snapshot imutável do perfil, com IDs das revisões dos fatos, para matching e geração.

## Regras de validade

`verified` significa que o candidato aprovou a afirmação e suas fontes para uso. Isso não significa verificação externa independente. Fatos `unverified`, `expired` ou `revoked` não alimentam geração factual. O período de validade é verificado em cada execução. Revogação invalida pacotes ainda não enviados e exige nova revisão.

Uma revisão cria novo ID de fato e incrementa a versão do perfil. Registros antigos usados por avaliações continuam referenciáveis, sujeitos à política de eliminação de dados pessoais. Audit logs preservam identificadores e hashes mínimos, não o texto sensível.

Restrições de imigração, autorização de trabalho, salário e disponibilidade devem estar em registros privados separados, com jurisdição, validade e revisão humana. A aplicação não infere direitos legais a partir de nacionalidade ou localização.

## Campos de entrada

| Grupo | Conteúdo | Se ausente |
|---|---|---|
| Preferências | Cargos, mercados, localidades, modalidade | Solicitar configuração; não inventar filtros |
| Experiência | Empregador, cargo, datas, responsabilidades comprovadas | Não gerar afirmações |
| Projetos | Repositório, papel pessoal, tecnologias, entregas | Não assumir autoria ou proficiência |
| Educação | Curso, instituição, datas e estado | Desconhecido |
| Restrições | Horas, autorização, sponsorship, disponibilidade, salário | Marcar revisão necessária |
| Evidências | Origem, hash, localização e data de revisão | Fato permanece não verificado |

## Retenção proposta

Documentos privados ativos: enquanto necessários à procura de trabalho. Conteúdo bruto de vagas e anexos: 90 dias por padrão. Pacotes rejeitados: 90 dias. Histórico de candidaturas encerradas: revisão de necessidade após 12 meses. Logs operacionais redigidos: 30 dias. Backups: janela de 30 dias, com reaplicação de eliminações após restauração. São escolhas iniciais de produto a confirmar, não prazos legais determinados.

Solicitar eliminação deve remover arquivos, embeddings, conteúdo dos fatos, caches e cópias em providers quando aplicável. Manter apenas auditoria mínima pseudonimizada quando justificada; não usar soft delete como substituto de eliminação.

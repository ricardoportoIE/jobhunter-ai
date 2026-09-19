# Contratos de dados v0.2.0

[domain.schema.json](domain.schema.json) usa JSON Schema Draft 2020-12 e contém seis entidades principais em `$defs`. É um contrato de design, não uma migration de banco nem implementação Pydantic.

| Entidade | Responsabilidade | Invariantes principais |
|---|---|---|
| Job | Snapshot de vaga, origem e requisitos | Campos desconhecidos null; URL não autoriza fetch; origem programática exige referência de revisão |
| CandidateFact | Afirmação atômica versionada | verified exige evidência, revisor, data e usos permitidos |
| Evidence | Referência e localização da fonte | Conteúdo privado por referência; revisão com ator e data |
| MatchResult | Score e cobertura reproduzíveis | Oito categorias; referências a versões de perfil/vaga e algoritmo |
| Application | Ciclo de candidatura | Pacote aprovado identificado por hash; envio manual separado de adapter |
| CandidateProfile | Snapshot e preferências | Fatos por ID de revisão; restrições e master CV ficam privados |

Todas as propriedades listadas são obrigatórias; quando desconhecidas, preencher null onde admitido. Arrays vazios representam ausência de registros. UUIDs são identificadores, instantes usam UTC com `Z`, scores ficam entre 0 e 100 e coverage/confidence entre 0 e 1. `additionalProperties: false` evita aceitar campos inesperados silenciosamente.

Na v0.2.0, MatchResult exige `employment_gate` e `review_flags`. A recomendação de procurar uma oferta é distinta da condição para começar a trabalhar. `REVIEW_BEFORE_START` exige pelo menos uma flag. Sponsorship desconhecido não impede recomendação positiva por si só. Dados locais foram migrados da v0.1.0 para a v0.2.0; ver [política](../docs/phase-0/matching-policy.md).

`confidence` de extração pode ser null e não equivale a evidência ou aprovação. `coverage` mede dados avaliados e não é probabilidade estatística. Referências `fixture://` e hashes repetidos do exemplo são placeholders declarados; em dados reais, calcular SHA-256 sobre os bytes canônicos especificados e guardar a referência resolvível em armazenamento autorizado.

## Regras que ainda precisam de validação no domínio

JSON Schema valida forma, tipos e algumas condições locais. Não valida por si só:

- Existência, ownership e revisão das evidências referenciadas; validade temporal e usos no momento da operação.
- `valid_until >= valid_from`, salário mínimo <= máximo e expiração posterior à decisão.
- Oito categorias distintas e pesos somando 100; correspondência entre assessments e requisitos; cálculo de score/coverage e blockers segundo [ADR-003](../docs/adr/0003-evidence-and-approval.md).
- Perfil reviewed com fatos/evidências válidos e restrições suficientes para o uso pretendido.
- Transições permitidas, coerência de eventos, idempotência e concorrência.
- Aprovação por ator autorizado, hash e versões atuais, escopo, destinatário, validade e campos sensíveis revisados.
- Invalidação de pacotes após revogação; reconciliação de tentativa de envio com resultado desconhecido.
- Segurança de URL, caminho e bytes de arquivos.

Essas regras entram nas histórias da fase 1 ou na fase que introduz a operação. O exemplo é verificado também quanto às referências e coerência básica, sem alegar que há um motor de domínio pronto.

## Versionamento

Mudança incompatível exige nova `schema_version` e migração explícita dos dados. IDs de revisões de fatos permanecem imutáveis. API poderá expor views menores e excluir conteúdo sensível; estes schemas não autorizam publicar todo o objeto no frontend.

## Validar

Executar `python scripts/validate_phase0.py` no ambiente com [requirements-phase0.txt](../requirements-phase0.txt). O script verifica metaschema, exemplos, referências do fixture, casos de rejeição e links locais da documentação. Não usa rede nem credenciais. A dependência `jsonschema` serve apenas para validação dos contratos nesta fase.

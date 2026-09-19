import { useEffect, useState } from "react";
import { api } from "./api";
import type { Fact, Job } from "./types";
import { Field } from "./ui";
import { useTask } from "./useTask";

type Hit = { id: string; kind: string; label: string; similarity: number };
export default function SemanticSearch({ facts }: { facts: Fact[] }) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [kind, setKind] = useState<"job" | "fact">("job");
  const [selected, setSelected] = useState("");
  const [consent, setConsent] = useState(false);
  const [hits, setHits] = useState<Hit[] | null>(null);
  const [indexed, setIndexed] = useState(0);
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [loadError, setLoadError] = useState("");
  const task = useTask();
  useEffect(() => {
    let active = true;
    api<{ items: Job[]; total: number }>(`/jobs?limit=100&offset=${offset}`)
      .then((result) => {
        if (active) {
          setJobs(result.items);
          setTotal(result.total);
          setLoadError("");
        }
      })
      .catch((error: Error) => {
        if (active) setLoadError(error.message);
      });
    return () => {
      active = false;
    };
  }, [offset]);
  const eligibleFacts = facts.filter(
    (f) =>
      f.status === "verified" &&
      f.allowed_uses.includes("matching") &&
      f.sensitivity !== "sensitive",
  );
  const options =
    kind === "job"
      ? jobs.map((j) => ({ ...j, label: j.title || j.raw_text.slice(0, 90) }))
      : eligibleFacts.map((f) => ({ ...f, label: f.claim }));
  return (
    <>
      <p className="eyebrow">PESQUISA POR SIGNIFICADO</p>
      <h1>Busca semântica</h1>
      <p>
        Encontre vagas ou fatos próximos da sua pesquisa. A similaridade ajuda a
        localizar evidências; não comprova atendimento a um requisito.
      </p>
      <section className="panel narrow">
        <Field label="Pesquisar em">
          <select
            value={kind}
            onChange={(event) => {
              setKind(event.target.value as "job" | "fact");
              setSelected("");
              setHits(null);
            }}
          >
            <option value="job">Vagas</option>
            <option value="fact">Fatos com evidências</option>
          </select>
        </Field>
        <label className="check">
          <input
            type="checkbox"
            checked={consent}
            onChange={(event) => setConsent(event.target.checked)}
          />
          Autorizo enviar à OpenAI o texto selecionado e a pesquisa para gerar
          embeddings.
        </label>
        <h2>Adicionar ao índice</h2>
        <p>
          Os vetores ficam no banco local. Edições deixam a versão anterior fora
          da busca; indexe novamente quando necessário. Fatos sensíveis ou sem
          evidência válida são excluídos.
        </p>
        {loadError && <p role="alert">{loadError}</p>}
        <Field label="Registro a indexar">
          <select
            value={selected}
            onChange={(event) => setSelected(event.target.value)}
          >
            <option value="">Selecione um registro</option>
            {options.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </Field>
        {kind === "job" && total > 100 && (
          <div className="actions">
            <button
              disabled={!offset}
              onClick={() => {
                setOffset(offset - 100);
                setSelected("");
              }}
            >
              Vagas anteriores
            </button>
            <button
              disabled={offset + 100 >= total}
              onClick={() => {
                setOffset(offset + 100);
                setSelected("");
              }}
            >
              Próximas vagas
            </button>
          </div>
        )}
        <button
          disabled={task.busy || !consent || !selected}
          onClick={() =>
            void task.run(async () => {
              const item = options.find((item) => item.id === selected)!;
              await api("/ai/index", "POST", {
                kind,
                source_id: item.id,
                expected_version: item.version,
                external_processing_confirmed: true,
              });
            }, "Registro indexado para pesquisa.")
          }
        >
          Indexar registro selecionado
        </button>
        <h2>Pesquisar</h2>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            const query = String(
              new FormData(event.currentTarget).get("query"),
            );
            void task.run(async () => {
              const result = await api<{
                items: Hit[];
                indexed_documents: number;
              }>("/ai/search", "POST", {
                query,
                kind,
                external_processing_confirmed: true,
              });
              setHits(result.items);
              setIndexed(result.indexed_documents);
            }, "Pesquisa concluída.");
          }}
        >
          <Field label="O que procura?">
            <input
              name="query"
              required
              maxLength={1000}
              placeholder="Ex.: APIs Python e bases de dados"
            />
          </Field>
          <button disabled={task.busy || !consent}>
            Buscar por significado
          </button>
        </form>
        {task.feedback}
      </section>
      {hits && (
        <section className="panel">
          <h2>Resultados</h2>
          <p>{indexed} registro(s) com índice válido.</p>
          {!hits.length && (
            <p>Sem resultados. Indexe um registro atual antes de pesquisar.</p>
          )}
          {hits.map((hit) => (
            <article key={hit.id}>
              <a href={hit.kind === "job" ? `#job/${hit.id}` : "#profile"}>
                {hit.label}
              </a>
              <p>Similaridade: {hit.similarity.toFixed(3)}</p>
            </article>
          ))}
        </section>
      )}
    </>
  );
}

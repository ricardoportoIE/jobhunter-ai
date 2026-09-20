import { t } from "./i18n";
import { useEffect, useState } from "react";
import { api } from "./api";
import type { Fact, Job } from "./types";
import { Field } from "./ui";
import { useAiTask } from "./useAiTask";
type Hit = {
  id: string;
  kind: string;
  label: string;
  similarity: number;
};
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
  const task = useAiTask(consent);
  useEffect(() => {
    let active = true;
    api<{
      items: Job[];
      total: number;
    }>(`/jobs?limit=100&offset=${offset}`)
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
      <p className="eyebrow">{t("SEARCH BY MEANING")}</p>
      <h1>{t("Semantic search")}</h1>
      <p>
        {t(
          "Find jobs or facts close to your search. Similarity helps locate evidence; it does not prove meeting a requirement.",
        )}
      </p>
      <section className="panel narrow">
        <Field label={t("Search in")}>
          <select
            value={kind}
            onChange={(event) => {
              setKind(event.target.value as "job" | "fact");
              setSelected("");
              setHits(null);
            }}
          >
            <option value="job">{t("Jobs")}</option>
            <option value="fact">{t("Facts with evidence")}</option>
          </select>
        </Field>
        <label className="check">
          <input
            type="checkbox"
            checked={consent}
            onChange={(event) => setConsent(event.target.checked)}
          />
          {t(
            "I authorise sending selected text and research to OpenAI to generate embeddings.",
          )}
        </label>
        <h2>{t("Add to index")}</h2>
        <p>
          {t(
            "Vectors remain in the local database. Edits exclude the previous version from search; reindex when necessary. Sensitive facts or those without valid evidence are excluded.",
          )}
        </p>
        {loadError && <p role="alert">{loadError}</p>}
        <Field label={t("Record to index")}>
          <select
            value={selected}
            onChange={(event) => setSelected(event.target.value)}
          >
            <option value="">{t("Select a record")}</option>
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
              {t("Previous jobs")}
            </button>
            <button
              disabled={offset + 100 >= total}
              onClick={() => {
                setOffset(offset + 100);
                setSelected("");
              }}
            >
              {t("Next vacancies")}
            </button>
          </div>
        )}
        <button
          disabled={task.busy || !consent || !selected}
          onClick={() =>
            void task.run(async (headers) => {
              const item = options.find((item) => item.id === selected)!;
              await api(
                "/ai/index",
                "POST",
                {
                  kind,
                  source_id: item.id,
                  expected_version: item.version,
                  external_processing_confirmed: true,
                },
                headers,
              );
            }, t("Record indexed for search."))
          }
        >
          {t("Index selected record")}
        </button>
        <h2>{t("Search")}</h2>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            const query = String(
              new FormData(event.currentTarget).get("query"),
            );
            void task.run(async (headers) => {
              const result = await api<{
                items: Hit[];
                indexed_documents: number;
              }>(
                "/ai/search",
                "POST",
                {
                  query,
                  kind,
                  external_processing_confirmed: true,
                },
                headers,
              );
              setHits(result.items);
              setIndexed(result.indexed_documents);
            }, t("Search completed."));
          }}
        >
          <Field label={t("What are you looking for?")}>
            <input
              name="query"
              required
              maxLength={1000}
              placeholder={t("E.g.: Python APIs and databases")}
            />
          </Field>
          <button disabled={task.busy || !consent}>
            {t("Search by meaning")}
          </button>
        </form>
        {task.feedback}
      </section>
      {hits && (
        <section className="panel">
          <h2>{t("Results")}</h2>
          <p>
            {indexed}
            {t(" record(s) with valid index.")}
          </p>
          {!hits.length && (
            <p>{t("No results. Index a current record before searching.")}</p>
          )}
          {hits.map((hit) => (
            <article key={hit.id}>
              <a href={hit.kind === "job" ? `#job/${hit.id}` : "#profile"}>
                {hit.label}
              </a>
              <p>
                {t("Similarity: ")}
                {hit.similarity.toFixed(3)}
              </p>
            </article>
          ))}
        </section>
      )}
    </>
  );
}

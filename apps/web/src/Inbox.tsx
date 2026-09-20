import { useTask } from "./useTask";
import { optional, value } from "./forms";
import { useEffect, useState } from "react";
import { api } from "./api";
import type { Job } from "./types";
import { ErrorState, Field, Loading } from "./ui";

export function Inbox() {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [archived, setArchived] = useState(false);
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [result, setResult] = useState<{ items: Job[]; total: number } | null>(
    null,
  );
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    api<{ items: Job[]; total: number }>(
      `/jobs?limit=20&offset=${offset}&q=${encodeURIComponent(query)}&archived=${archived}${status ? "&status=" + status : ""}`,
    )
      .then((data) => {
        if (active) {
          setResult(data);
          setError("");
        }
      })
      .catch((reason: Error) => {
        if (active) setError(reason.message);
      });
    return () => {
      active = false;
    };
  }, [query, status, archived, offset, refresh]);
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">OPORTUNIDADES</p>
          <h1>Sua Inbox</h1>
          <p>Uma oportunidade de cada vez, com decisões rastreáveis.</p>
        </div>
        <a className="button primary" href="#import">
          Importar vaga
        </a>
      </div>
      <form
        className="filters"
        onSubmit={(event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          setResult(null);
          setQuery(value(form, "q"));
          setStatus(value(form, "status"));
          setArchived(form.has("archived"));
          setOffset(0);
          setRefresh(refresh + 1);
        }}
      >
        <Field label="Buscar título ou empresa">
          <input name="q" placeholder="Ex.: Junior Python" />
        </Field>
        <Field label="Estágio">
          <select name="status">
            <option value="">Todos</option>
            <option value="DISCOVERED">Importada</option>
            <option value="PARSED">Revisada</option>
            <option value="SCORED">Analisada</option>
          </select>
        </Field>
        <label className="check">
          <input type="checkbox" name="archived" />
          Arquivadas
        </label>
        <button>Filtrar</button>
      </form>
      {error ? (
        <ErrorState error={error} retry={() => setRefresh(refresh + 1)} />
      ) : !result ? (
        <Loading />
      ) : (
        <>
          <p className="muted">{result.total} oportunidade(s)</p>
          {!result.items.length ? (
            <section className="empty">
              <h2>Nenhuma vaga nesta seleção</h2>
              <p>
                Importe o texto de um anúncio para começar ou ajuste os filtros.
              </p>
              <a href="#import">Importar primeira vaga →</a>
            </section>
          ) : (
            <ul className="job-list">
              {result.items.map((job) => (
                <li key={job.id}>
                  <a href={`#job/${job.id}`}>
                    <div>
                      <span className="tag">
                        {
                          {
                            DISCOVERED: "Importada",
                            PARSED: "Revisada",
                            SCORED: "Analisada",
                          }[job.status]
                        }
                      </span>
                      <h2>{job.title || "Vaga aguardando revisão"}</h2>
                      <p>
                        {job.company_name || "Empresa não informada"} ·{" "}
                        {job.location || "Local não informado"}
                      </p>
                    </div>
                    <span aria-hidden="true">↗</span>
                  </a>
                </li>
              ))}
            </ul>
          )}
          <div className="actions">
            <button
              disabled={offset === 0}
              onClick={() => {
                setResult(null);
                setOffset(Math.max(0, offset - 20));
              }}
            >
              Anterior
            </button>
            <button
              disabled={offset + 20 >= result.total}
              onClick={() => {
                setResult(null);
                setOffset(offset + 20);
              }}
            >
              Próxima
            </button>
          </div>
        </>
      )}
    </>
  );
}

export function ImportJob() {
  const task = useTask();
  const [key] = useState(() => crypto.randomUUID());
  const [mode, setMode] = useState<"text" | "url">("url");
  const [imported, setImported] = useState<Job | null>(null);
  return (
    <>
      <p className="eyebrow">NOVA OPORTUNIDADE</p>
      <h1>Importar anúncio</h1>
      <p>
        Cole o texto e registre a origem. Os campos serão revisados por você na
        próxima tela.
      </p>
      <section className="panel narrow">
        <nav className="tabs" aria-label="Import method">
          <button
            aria-pressed={mode === "url"}
            disabled={task.busy}
            onClick={() => setMode("url")}
          >
            From a link
          </button>
          <button
            aria-pressed={mode === "text"}
            disabled={task.busy}
            onClick={() => setMode("text")}
          >
            Paste text
          </button>
        </nav>
        {mode === "url" && (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              const data = new FormData(event.currentTarget);
              void task.run(async () => {
                const result = await api<{
                  job: Job;
                  extraction_error: string | null;
                }>("/jobs/import-url", "POST", {
                  url: String(data.get("url")),
                  ai_consent: data.has("ai_consent"),
                });
                if (result.extraction_error) {
                  setImported(result.job);
                  throw new Error(
                    "The advert was imported, but AI extraction could not finish. Open the job to review it manually or retry extraction from its details.",
                  );
                }
                window.location.hash = `job/${result.job.id}`;
              }, "Advert extracted. Review the draft fields before confirming.");
            }}
          >
            <Field label="Public vacancy link">
              <input
                name="url"
                type="url"
                required
                maxLength={2000}
                placeholder="https://careers.example.com/jobs/123"
              />
            </Field>
            <p>
              We read the public page and use AI to draft its fields and
              requirements. Missing information stays unknown. Pages requiring
              login, CAPTCHA or JavaScript may need pasted text.
            </p>
            <label className="check">
              <input type="checkbox" name="ai_consent" required />I authorise
              reading this public page and sending its text to OpenAI for
              extraction.
            </label>
            {task.feedback}
            {imported && (
              <a className="button" href={`#job/${imported.id}`}>
                Open imported job for review
              </a>
            )}
            <button className="primary" disabled={task.busy}>
              {task.busy ? "Reading and extracting…" : "Extract from link"}
            </button>
          </form>
        )}
        {mode === "text" && (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              const data = new FormData(event.currentTarget);
              void task.run(async () => {
                const job = await api<Job>(
                  "/jobs/import",
                  "POST",
                  {
                    raw_text: String(data.get("raw_text")),
                    source_name: value(data, "source_name") || "manual",
                    source_url: optional(data, "source_url"),
                    external_id: optional(data, "external_id"),
                    location_hint: optional(data, "location_hint"),
                  },
                  { "Idempotency-Key": key },
                );
                window.location.hash = `job/${job.id}`;
              }, "Vaga importada.");
            }}
          >
            <Field label="Texto original da vaga">
              <textarea name="raw_text" rows={12} required maxLength={50000} />
            </Field>
            <div className="form-grid">
              <Field label="Fonte">
                <input
                  name="source_name"
                  placeholder="Site da empresa, portal…"
                  maxLength={200}
                />
              </Field>
              <Field label="ID na fonte (opcional)">
                <input name="external_id" maxLength={200} />
              </Field>
            </div>
            <Field label="URL de origem (opcional)">
              <input type="url" name="source_url" maxLength={2000} />
            </Field>
            <Field label="Localidade do anúncio (opcional)">
              <input
                name="location_hint"
                placeholder="Ajuda a distinguir anúncios em cidades diferentes"
                maxLength={200}
              />
            </Field>
            {task.feedback}
            <button className="primary" disabled={task.busy}>
              {task.busy ? "Importando…" : "Importar e revisar"}
            </button>
          </form>
        )}
      </section>
    </>
  );
}

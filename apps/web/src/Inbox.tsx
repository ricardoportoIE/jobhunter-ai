import { t } from "./i18n";
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
  const [result, setResult] = useState<{
    items: Job[];
    total: number;
  } | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    api<{
      items: Job[];
      total: number;
    }>(
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
          <p className="eyebrow">{t("OPPORTUNITIES")}</p>
          <h1>{t("Your Inbox")}</h1>
          <p>{t("One opportunity at a time, with traceable decisions.")}</p>
        </div>
        <a className="button primary" href="#import">
          {t("Import vacancy")}
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
        <Field label={t("Search title or company")}>
          <input name="q" placeholder={t("E.g.: Junior Python")} />
        </Field>
        <Field label={t("Stage")}>
          <select name="status">
            <option value="">{t("All")}</option>
            <option value="DISCOVERED">{t("Imported")}</option>
            <option value="PARSED">{t("Reviewed")}</option>
            <option value="SCORED">{t("Analysed")}</option>
          </select>
        </Field>
        <label className="check">
          <input type="checkbox" name="archived" />
          {t("Archived")}
        </label>
        <button>{t("Filter")}</button>
      </form>
      {error ? (
        <ErrorState error={error} retry={() => setRefresh(refresh + 1)} />
      ) : !result ? (
        <Loading />
      ) : (
        <>
          <p className="muted">
            {result.total}
            {t(" opportunity(ies)")}
          </p>
          {!result.items.length ? (
            <section className="empty">
              <h2>{t("No vacancies in this selection")}</h2>
              <p>
                {t("Import an advert to get started, or adjust the filters.")}
              </p>
              <a href="#import">{t("Import first vacancy \u2192")}</a>
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
                            DISCOVERED: t("Imported"),
                            PARSED: t("Reviewed"),
                            SCORED: t("Analysed"),
                          }[job.status]
                        }
                      </span>
                      <h2>{job.title || t("Job awaiting review")}</h2>
                      <p>
                        {job.company_name || t("Company not provided")} ·{" "}
                        {job.location || t("Location not provided")}
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
              {t("Previous")}
            </button>
            <button
              disabled={offset + 20 >= result.total}
              onClick={() => {
                setResult(null);
                setOffset(offset + 20);
              }}
            >
              {t("Next")}
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
      <p className="eyebrow">{t("NEW OPPORTUNITY")}</p>
      <h1>{t("Import advert")}</h1>
      <p>
        {t(
          "Start with a public vacancy link, or paste the advert text. Review the extracted details in the next step.",
        )}
      </p>
      <section className="panel narrow">
        <nav className="tabs" aria-label={t("Import method")}>
          <button
            aria-pressed={mode === "url"}
            disabled={task.busy}
            onClick={() => setMode("url")}
          >
            {t("From a link")}
          </button>
          <button
            aria-pressed={mode === "text"}
            disabled={task.busy}
            onClick={() => setMode("text")}
          >
            {t("Paste text")}
          </button>
        </nav>
        {
          <form
            hidden={mode !== "url"}
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
                    t(
                      "The advert was imported, but AI extraction could not finish. Open the job to review it manually or retry extraction from its details.",
                    ),
                  );
                }
                window.location.hash = `job/${result.job.id}`;
              }, t("Advert extracted. Review the draft fields before confirming."));
            }}
          >
            <Field label={t("Public vacancy link")}>
              <input
                name="url"
                type="url"
                required
                maxLength={2000}
                placeholder="https://careers.example.com/jobs/123"
              />
            </Field>
            <p>
              {t(
                "We read the public page and use AI to draft its fields and requirements. Missing information stays unknown. Pages requiring login, CAPTCHA or JavaScript may need pasted text.",
              )}
            </p>
            <label className="check">
              <input type="checkbox" name="ai_consent" required />
              {t(
                "I authorise reading this public page and sending its text to OpenAI for extraction.",
              )}
            </label>
            {task.feedback}
            {imported && (
              <a className="button" href={`#job/${imported.id}`}>
                {t("Open imported job for review")}
              </a>
            )}
            <button className="primary" disabled={task.busy}>
              {task.busy
                ? t("Reading and extracting\u2026")
                : t("Extract from link")}
            </button>
          </form>
        }
        {
          <form
            hidden={mode !== "text"}
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
              }, t("Job imported."));
            }}
          >
            <Field label={t("Original job text")}>
              <textarea name="raw_text" rows={12} required maxLength={50000} />
            </Field>
            <div className="form-grid">
              <Field label={t("Source")}>
                <input
                  name="source_name"
                  placeholder={t("Company website, portal\u2026")}
                  maxLength={200}
                />
              </Field>
              <Field label={t("ID at source (optional)")}>
                <input name="external_id" maxLength={200} />
              </Field>
            </div>
            <Field label={t("Source URL (optional)")}>
              <input type="url" name="source_url" maxLength={2000} />
            </Field>
            <Field label={t("Advert location (optional)")}>
              <input
                name="location_hint"
                placeholder={t("Helps distinguish adverts in different cities")}
                maxLength={200}
              />
            </Field>
            {task.feedback}
            <button className="primary" disabled={task.busy}>
              {task.busy ? t("Importing\u2026") : t("Import and review")}
            </button>
          </form>
        }
      </section>
    </>
  );
}

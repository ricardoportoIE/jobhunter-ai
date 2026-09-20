import { t } from "./i18n";
import { useTask } from "./useTask";
import { optional, value } from "./forms";
import { useState } from "react";
import { api } from "./api";
import type { Job } from "./types";
import { Field } from "./ui";
export { default as Inbox } from "./Opportunities";
export function ImportJob({ initialUrl = "" }: { initialUrl?: string }) {
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
                defaultValue={initialUrl}
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
            <details className="disclosure">
              <summary>{t("Source details (optional)")}</summary>
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
                  placeholder={t(
                    "Helps distinguish adverts in different cities",
                  )}
                  maxLength={200}
                />
              </Field>
            </details>
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

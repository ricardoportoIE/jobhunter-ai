import { t, localisedLabels } from "./i18n";
import { useEffect, useState } from "react";
import { api } from "./api";
import type { Job } from "./types";
import { useAiTask } from "./useAiTask";
import { ErrorState, Loading } from "./ui";
export type AiStatus = {
  configured: boolean;
  model: string;
  tasks?: Record<
    string,
    {
      model: string;
      effort: string | null;
    }
  >;
  budget: {
    spent_eur: string;
    reserved_eur: string;
    limit_eur: string;
    unreconciled: boolean;
    alerts: number[];
  };
};
type Citation = {
  quote: string;
  confidence: number;
};
export type Extraction = {
  run_id: string;
  stale?: boolean;
  result: {
    fields: Record<string, unknown>;
    citations: Record<string, Citation>;
    requirements: {
      text: string;
      citation: Citation;
    }[];
    risk_flags: string[];
    job_version: number;
  };
};
const labels: Record<string, string> = localisedLabels({
  title: "Title",
  company_name: "Company",
  location: "Location",
  country: "Country",
  work_mode: "Working arrangement",
  employment_type: "Contract",
  seniority: "Level",
  work_authorisation: "Authorisation",
  sponsorship: "Sponsorship",
  salary: "Salary",
});
function Quote({ citation }: { citation?: Citation }) {
  return citation ? (
    <>
      <blockquote>{citation.quote}</blockquote>
      <small>
        {t("Confidence declared by AI: ")}
        {Math.round(citation.confidence * 100)}%
        {citation.confidence < 0.75 ? t(" \u00B7 Priority review") : ""}
      </small>
    </>
  ) : (
    <small>{t("No information in the listing.")}</small>
  );
}
export function AiJobTools({ job, saved }: { job: Job; saved: () => void }) {
  const [extraction, setExtraction] = useState<Extraction | null>(null);
  const task = useAiTask();
  useEffect(() => {
    let active = true;
    api<Extraction | null>(`/ai/jobs/${job.id}/extraction`)
      .then((result) => {
        if (active) setExtraction(result);
      })
      .catch(() => {
        /* Optional history; explicit actions report errors below. */
      });
    return () => {
      active = false;
    };
  }, [job.id, job.version]);
  const stale = extraction && extraction.result.job_version !== job.version;
  return (
    <section className="panel ai-panel">
      <p className="eyebrow">{t("READING ASSISTANT")}</p>
      <h2>{t("Extract fields with AI")}</h2>
      <p>
        {t(
          "Sends this job text to OpenAI. Extraction remains a suggestion until you review. Confidence indicates the model's estimate; it is not a validated probability.",
        )}
      </p>
      <button
        disabled={task.busy}
        onClick={() =>
          void task.run(async (headers) => {
            setExtraction(
              await api<Extraction>(
                `/ai/jobs/${job.id}/parse`,
                "POST",
                {
                  expected_version: job.version,
                },
                headers,
              ),
            );
          }, t("Extraction available for review."))
        }
      >
        {task.busy ? t("Processing\u2026") : t("Extract with AI")}
      </button>
      {task.feedback}
      {extraction && (
        <details open={!stale}>
          <summary>{t("Check suggestions and source excerpts")}</summary>
          {stale && (
            <p role="status">
              {t(
                "This extraction corresponds to a previous version of the job.",
              )}
            </p>
          )}
          <div className="ai-fields">
            {Object.entries(extraction.result.fields)
              .sort(
                ([a], [b]) =>
                  Object.keys(labels).indexOf(a) -
                  Object.keys(labels).indexOf(b),
              )
              .map(([name, value]) => (
                <article key={name}>
                  <h3>{labels[name] || name}</h3>
                  <p>
                    {value === null
                      ? t("Unknown")
                      : typeof value === "object"
                        ? Object.entries(value as Record<string, unknown>)
                            .filter(([, v]) => v !== null)
                            .map(([k, v]) => `${k}: ${String(v)}`)
                            .join(" · ")
                        : String(value)}
                  </p>
                  <Quote citation={extraction.result.citations[name]} />
                </article>
              ))}
          </div>
          <h3>{t("Suggested requirements")}</h3>
          {extraction.result.requirements.map((item, index) => (
            <article key={index}>
              <p>
                <strong>{item.text}</strong>
              </p>
              <Quote citation={item.citation} />
            </article>
          ))}
          {extraction.result.risk_flags.map((flag) => (
            <p key={flag}>{flag}</p>
          ))}
          <button
            disabled={task.busy || !!stale}
            onClick={() =>
              void task.run(async () => {
                await api(`/ai/jobs/${job.id}/draft`, "POST", {
                  expected_version: job.version,
                  run_id: extraction.run_id,
                });
                saved();
              }, t("Draft filled. Review the fields below and confirm the review."))
            }
          >
            {t("Fill in draft for review")}
          </button>
        </details>
      )}
    </section>
  );
}
type Run = {
  execution_config?: {
    effort?: string | null;
  };
  usage?: {
    reasoning_tokens: number;
    cached_input_tokens: number;
    web_search_calls: number;
  };
  id: string;
  operation: string;
  model: string;
  status: string;
  actual_eur: string | null;
  reserved_eur: string;
  input_tokens: number | null;
  output_tokens: number | null;
  latency_ms: number | null;
  error_code: string | null;
};
const operations: Record<string, string> = localisedLabels({
  suggest_review: "Second assessment",
  research: "Public search",
  strategy: "Application strategy",
  parse: "Extraction",
  cv_extract: "CV extraction",
  ui_translate: "Interface translation",
  suggest: "Matching suggestion",
  embed: "Indexing or search",
});
const states: Record<string, string> = localisedLabels({
  succeeded: "Completed",
  running: "In progress",
  failed: "Not completed",
  invalid: "Response rejected",
  uncertain: "Cost to check",
});
export function AiActivity() {
  const [data, setData] = useState<{
    status: AiStatus;
    runs: Run[];
  } | null>(null);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    let active = true;
    Promise.all([api<AiStatus>("/ai/status"), api<Run[]>("/ai/runs")])
      .then(([status, runs]) => {
        if (active) {
          setData({ status, runs });
          setError("");
        }
      })
      .catch((reason: Error) => {
        if (active) setError(reason.message);
      });
    return () => {
      active = false;
    };
  }, [refresh]);
  if (error)
    return <ErrorState error={error} retry={() => setRefresh(refresh + 1)} />;
  if (!data) return <Loading />;
  const { status, runs } = data;
  return (
    <>
      <p className="eyebrow">{t("USAGE CONTROL")}</p>
      <h1>{t("AI activity")}</h1>
      <section className="panel">
        <p>
          {status.configured
            ? t("OpenAI configured")
            : t("Key not yet configured")}{" "}
          · {status.model}
        </p>
        <h2>{t("Monthly budget")}</h2>
        {status.tasks && (
          <ul>
            {Object.entries(status.tasks).map(([task, policy]) => (
              <li key={task}>
                {operations[task] ?? task}: {policy.model}
                {policy.effort ? ` · ${policy.effort}` : ""}
              </li>
            ))}
          </ul>
        )}
        <p>
          {t("Accounted usage: \u20AC")}
          {Number(status.budget.spent_eur).toFixed(4)}
          {t(" \u00B7 Reserved: \u20AC")}
          {Number(status.budget.reserved_eur).toFixed(4)}
          {t(" \u00B7 Limit: \u20AC")}
          {status.budget.limit_eur}
        </p>
        <p>
          {t(
            "Conservative project estimate; not the account invoice. Combined control also preserves \u20AC15 for AWS within the \u20AC25 cap.",
          )}
        </p>
        {status.budget.alerts.map((level) => (
          <p key={level} role="status">
            {t("AI usage reached ")}
            {level}
            {t("% of the limit.")}
          </p>
        ))}
        {status.budget.unreconciled && (
          <p role="alert">
            {t(
              "New calls are blocked because a cost is unknown. Check provider usage and reconcile it through local administration.",
            )}
          </p>
        )}
        <button onClick={() => setRefresh(refresh + 1)}>
          {t("Update activity")}
        </button>
      </section>
      <h2>{t("Recent runs")}</h2>
      {!runs.length && <p>{t("No calls made.")}</p>}
      {runs.map((run) => (
        <article className="panel" key={run.id}>
          <h3>
            {operations[run.operation] ?? run.operation} ·{" "}
            {states[run.status] ?? run.status}
          </h3>
          <p>
            {run.model}
            {run.execution_config?.effort
              ? ` · ${run.execution_config.effort}`
              : ""}
          </p>
          {run.usage && (
            <p>
              {t("Reasoning: ")}
              {run.usage.reasoning_tokens}
              {t(" tokens \u00B7 Cached input: ")}
              {run.usage.cached_input_tokens}
              {t(" tokens \u00B7 Web searches:")} {run.usage.web_search_calls}
            </p>
          )}
          <p>
            €{Number(run.actual_eur ?? run.reserved_eur).toFixed(6)}
            {run.actual_eur === null ? " reservados" : " contabilizados"} ·
            {run.input_tokens ?? "?"}
            {t(" input tokens \u00B7")} {run.output_tokens ?? "?"}
            {t(" output tokens \u00B7")}
            {run.latency_ms ?? "?"} ms
          </p>
          {run.error_code && <p>{run.error_code}</p>}
          <small>
            {t("Execution: ")}
            {run.id}
          </small>
        </article>
      ))}
    </>
  );
}

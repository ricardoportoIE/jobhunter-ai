import { t, dateLocale } from "./i18n";
import { useEffect, useState, type ReactNode } from "react";
import { api } from "./api";
import type { Job } from "./types";
import { useAiTask } from "./useAiTask";
type Research = {
  run_id: string;
  stale: boolean;
  result: {
    question: string;
    answer: string;
    retrieved_at: string;
    refresh_after: string;
    citations: {
      url: string;
      title: string;
      start: number;
      end: number;
    }[];
  };
};
function CitedAnswer({ result }: { result: Research["result"] }) {
  const chars = Array.from(result.answer);
  const parts: ReactNode[] = [];
  let cursor = 0;
  [...result.citations]
    .sort((a, b) => a.start - b.start)
    .forEach((citation, index) => {
      if (citation.start < cursor || citation.end > chars.length) return;
      parts.push(chars.slice(cursor, citation.start).join(""));
      parts.push(
        <a
          key={`${citation.start}:${index}`}
          href={citation.url}
          target="_blank"
          rel="noopener noreferrer"
          title={citation.title}
          aria-label={t("Source: {0}", [citation.title])}
        >
          [{index + 1}]
        </a>,
      );
      cursor = citation.end;
    });
  parts.push(chars.slice(cursor).join(""));
  return <p className="preserve">{parts}</p>;
}
export default function ResearchPanel({ job }: { job: Job }) {
  const [question, setQuestion] = useState("");
  const [domains, setDomains] = useState(
    "gov.ie, enterprise.gov.ie, irishimmigration.ie, gov.uk",
  );
  const [consent, setConsent] = useState(false);
  const [history, setHistory] = useState<Research[]>([]);
  const [error, setError] = useState("");
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 60000);
    return () => window.clearInterval(timer);
  }, []);
  const task = useAiTask(consent);
  useEffect(() => {
    let active = true;
    api<Research[]>(`/jobs/${job.id}/research`)
      .then((items) => {
        if (active) setHistory(items);
      })
      .catch((reason: Error) => {
        if (active) setError(reason.message);
      });
    return () => {
      active = false;
    };
  }, [job.id, job.version]);
  return (
    <section className="panel">
      <h2>{t("Consult updated public information")}</h2>
      <p>
        {t(
          "Send only one public question, without personal data. The search uses the indicated domains and returns sources for your checking. Profile facts and compatibility remain subject to review.",
        )}
      </p>
      <label>
        {t("Public question")}
        <textarea
          maxLength={1200}
          value={question}
          onChange={(event) => {
            setQuestion(event.target.value);
            setConsent(false);
          }}
        />
      </label>
      <label>
        {t("Source domains, separated by commas")}
        <input
          value={domains}
          onChange={(event) => {
            setDomains(event.target.value);
            setConsent(false);
          }}
        />
      </label>
      <label className="check">
        <input
          type="checkbox"
          checked={consent}
          onChange={(event) => setConsent(event.target.checked)}
        />
        {t(
          "I authorise sending this public question to OpenAI and web search.",
        )}
      </label>
      <button
        disabled={task.busy || !consent || question.trim().length < 10}
        onClick={() =>
          void task.run(async (headers) => {
            const value = await api<Research>(
              `/jobs/${job.id}/research`,
              "POST",
              {
                expected_version: job.version,
                question,
                allowed_domains: domains
                  .split(",")
                  .map((s) => s.trim())
                  .filter(Boolean),
                external_processing_confirmed: true,
              },
              headers,
            );
            setHistory((items) => [
              value,
              ...items.filter((item) => item.run_id !== value.run_id),
            ]);
            setError("");
          }, t("Search available for review."))
        }
      >
        {task.busy ? t("Searching\u2026") : t("Search public sources")}
      </button>
      {task.feedback}
      {error && <p role="alert">{error}</p>}
      {history.map((item) => (
        <details key={item.run_id} open>
          <summary>{item.result.question}</summary>
          <p>
            {t("Consulted on")}{" "}
            {new Date(item.result.retrieved_at).toLocaleString(dateLocale())}
            {t(" \u00B7 Human review required")}
          </p>
          {(item.stale || Date.parse(item.result.refresh_after) <= now) && (
            <p role="status">
              {t("Old query: search again before using decisive information.")}
            </p>
          )}
          <CitedAnswer result={item.result} />
          <ul>
            {item.result.citations.map((citation, index) => (
              <li key={index}>
                <a
                  href={citation.url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {citation.title || citation.url}
                </a>
              </li>
            ))}
          </ul>
        </details>
      ))}
    </section>
  );
}

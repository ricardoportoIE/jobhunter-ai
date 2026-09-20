import { t } from "./i18n";
import { useState } from "react";
import { api } from "./api";
import {
  outcomes,
  type Assessment,
  type Fact,
  type Job,
  type Profile,
} from "./types";
import { useAiTask } from "./useAiTask";
type Suggestion = {
  run_id: string | null;
  stale: boolean;
  result: {
    assessments: (Assessment & {
      confidence: number;
      citations: {
        fact_id: string;
        evidence_id: string;
        fact_quote: string;
        evidence_quote: string;
      }[];
    })[];
    limitations: string[];
  };
};
export default function AiMatching({
  job,
  profile,
  facts,
  apply,
  changed,
}: {
  job: Job;
  profile: Profile;
  facts: Fact[];
  apply: (assessments: Assessment[], run: string | null) => void;
  changed?: () => void;
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const [consent, setConsent] = useState(false);
  const [suggestion, setSuggestion] = useState<Suggestion | null>(null);
  const [previous, setPrevious] = useState<Suggestion | null>(null);
  const task = useAiTask(consent);
  const available = facts.filter(
    (f) =>
      f.status === "verified" &&
      f.allowed_uses.includes("matching") &&
      f.sensitivity !== "sensitive",
  );
  return (
    <section className="ai-panel">
      <h3>{t("Suggestions with evidence")}</h3>
      <p>
        {t(
          "Select facts that AI can evaluate. The job title, description, requirements, selected statements and excerpts of your evidence will be sent to OpenAI. Data marked as sensitive is excluded; file names and local references remain here.",
        )}
      </p>
      <fieldset>
        <legend>{t("Facts authorised for this query")}</legend>
        {available.map((fact) => (
          <label className="check" key={fact.id}>
            <input
              type="checkbox"
              checked={selected.includes(fact.id)}
              disabled={
                task.busy ||
                (!selected.includes(fact.id) && selected.length >= 20)
              }
              onChange={(event) => {
                setConsent(false);
                setSelected((previous) =>
                  event.target.checked
                    ? [...previous, fact.id]
                    : previous.filter((id) => id !== fact.id),
                );
              }}
            />
            {fact.claim}
          </label>
        ))}
        {!available.length && (
          <p>
            {t(
              "No eligible facts available. Record evidence and publish the profile.",
            )}
          </p>
        )}
      </fieldset>
      <label className="check">
        <input
          type="checkbox"
          checked={consent}
          onChange={(event) => setConsent(event.target.checked)}
        />
        {t(
          "I authorise sending the job, selected facts and their evidence snippets to OpenAI.",
        )}
      </label>
      <button
        disabled={task.busy || !consent}
        onClick={() =>
          void task.run(async (headers) => {
            setPrevious(suggestion);
            setSuggestion(
              await api<Suggestion>(
                `/ai/jobs/${job.id}/suggest`,
                "POST",
                {
                  job_version: job.version,
                  profile_version: profile.version,
                  fact_ids: selected,
                  external_processing_confirmed: true,
                },
                headers,
              ),
            );
            changed?.();
          }, t("Suggestions ready for review."))
        }
      >
        {task.busy ? t("Evaluating\u2026") : t("Suggest assessments with AI")}
      </button>
      <button
        disabled={task.busy || !consent || !suggestion}
        onClick={() =>
          void task.run(async (headers) => {
            const value = await api<Suggestion>(
              `/ai/jobs/${job.id}/suggest`,
              "POST",
              {
                job_version: job.version,
                profile_version: profile.version,
                fact_ids: selected,
                external_processing_confirmed: true,
                independent_review: true,
              },
              headers,
            );
            setPrevious(suggestion);
            setSuggestion(value);
            changed?.();
          }, t("Second assessment available. Check disagreements before deciding."))
        }
      >
        {t("Request a second assessment")}
      </button>
      {task.feedback}
      {previous && (
        <details>
          <summary>{t("Previous evaluation preserved")}</summary>
          {previous.result.assessments.map((item) => (
            <p key={item.requirement_id}>
              <strong>{outcomes[item.status]}</strong> · {item.reason}
            </p>
          ))}
        </details>
      )}
      {suggestion && (
        <>
          {suggestion.stale && (
            <p role="alert">
              {t("The job or profile has changed. Generate a new suggestion.")}
            </p>
          )}
          {suggestion.result.assessments.map((item) => (
            <article key={item.requirement_id}>
              <h4>
                {
                  job.requirements.find((r) => r.id === item.requirement_id)
                    ?.text
                }{" "}
                · {outcomes[item.status]}
              </h4>
              <p>{item.reason}</p>
              <small>
                {t("Declared confidence: ")}
                {Math.round(item.confidence * 100)}
                {t("% (not calibrated)")}
              </small>
              {item.citations.map((citation, index) => (
                <details key={index}>
                  <summary>{t("Check fact and evidence")}</summary>
                  <p>
                    {t("Fact: ")}
                    {citation.fact_quote}
                  </p>
                  <blockquote>{citation.evidence_quote}</blockquote>
                </details>
              ))}
            </article>
          ))}
          {suggestion.result.limitations.map((item) => (
            <p key={item}>{item}</p>
          ))}
          <button
            disabled={task.busy || suggestion.stale}
            onClick={() => {
              apply(
                suggestion.result.assessments.map(
                  ({ requirement_id, status, reason, fact_ids }) => ({
                    requirement_id,
                    status,
                    reason,
                    fact_ids,
                  }),
                ),
                suggestion.run_id,
              );
            }}
          >
            {t("Fill in assessments for my review")}
          </button>
        </>
      )}
    </section>
  );
}

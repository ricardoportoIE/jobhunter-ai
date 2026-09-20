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
import { eligibleMatchingFacts } from "./eligibleFacts";
import Icon from "./Icon";
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
  const [selected, setSelected] = useState<string[]>(() =>
    eligibleMatchingFacts(facts)
      .slice(0, 20)
      .map((fact) => fact.id),
  );
  const [consent, setConsent] = useState(false);
  const [suggestion, setSuggestion] = useState<Suggestion | null>(null);
  const [previous, setPrevious] = useState<Suggestion | null>(null);
  const context = JSON.stringify([
    job.id,
    job.version,
    profile.version,
    selected,
  ]);
  const [suggestionContext, setSuggestionContext] = useState("");
  const task = useAiTask(consent && selected.length > 0, context);
  const selectionChanged = suggestionContext !== context;
  const available = eligibleMatchingFacts(facts);
  return (
    <section className="ai-panel">
      <h3>
        <Icon name="sparkle" />
        {t("Let AI help with the first pass")}
      </h3>
      <p>
        {t(
          "{0} approved facts selected. AI will suggest how your experience fits; you review the assessment before calculating a result.",
          [selected.length],
        )}
      </p>
      {available.length > 20 && (
        <p role="note">
          {t(
            "The first 20 eligible facts are selected. Choose the most relevant facts before continuing.",
          )}
        </p>
      )}
      <details className="disclosure">
        <summary>{t("Choose facts and review what is shared")}</summary>
        <p>
          {t(
            "Select facts that AI can evaluate. The job title, description, requirements, selected statements and excerpts of your evidence will be sent to OpenAI. Data marked as sensitive is excluded; file names and local references remain here.",
          )}
        </p>
        <fieldset>
          <legend>{t("Facts authorised for this query")}</legend>
          <div className="actions">
            <button
              disabled={task.busy}
              onClick={() => {
                setSelected(available.slice(0, 20).map((fact) => fact.id));
                setConsent(false);
              }}
            >
              {t("Select eligible facts")}
            </button>
            <button
              disabled={task.busy}
              onClick={() => {
                setSelected([]);
                setConsent(false);
              }}
            >
              {t("Clear selection")}
            </button>
          </div>
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
      </details>
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
        className="primary"
        disabled={task.busy || !consent || !selected.length}
        onClick={() =>
          void task.run(async (headers) => {
            setPrevious(suggestion);
            const result = await api<Suggestion>(
              `/ai/jobs/${job.id}/suggest`,
              "POST",
              {
                job_version: job.version,
                profile_version: profile.version,
                fact_ids: selected,
                external_processing_confirmed: true,
              },
              headers,
            );
            setSuggestion(result);
            setSuggestionContext(context);
            if (!suggestion && !result.stale) {
              apply(
                result.result.assessments.map(
                  ({ requirement_id, status, reason, fact_ids }) => ({
                    requirement_id,
                    status,
                    reason,
                    fact_ids,
                  }),
                ),
                result.run_id,
              );
            }
            changed?.();
          }, t("Suggestions ready for review."))
        }
      >
        {task.busy ? t("Evaluating\u2026") : t("Suggest assessments with AI")}
      </button>
      {suggestion && (
        <button
          disabled={task.busy || !consent || !suggestion || selectionChanged}
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
              setSuggestionContext(context);
              changed?.();
            }, t("Second assessment available. Check disagreements before deciding."))
          }
        >
          {t("Request a second assessment")}
        </button>
      )}
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
          {(suggestion.stale || selectionChanged) && (
            <p role="alert">
              {t(
                "The job, profile or fact selection has changed. Generate a new suggestion.",
              )}
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
          {!previous && !selectionChanged && !suggestion.stale && (
            <p role="note">
              {t(
                "The first suggestions have filled your draft below. Check the evidence and confirm your assessment before calculating.",
              )}
            </p>
          )}
          <button
            disabled={task.busy || suggestion.stale || selectionChanged}
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

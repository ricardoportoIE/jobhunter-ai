import { t } from "./i18n";
import { useState } from "react";
import { api } from "./api";
import type { Job } from "./types";
import { useTask } from "./useTask";
type Candidate = {
  job: Job;
  lexical_similarity: number;
  semantic_similarity: number | null;
  conflicts: string[];
  shared_identity: boolean;
};
export default function DuplicateReview({
  job,
  saved,
}: {
  job: Job;
  saved: () => void;
}) {
  const [items, setItems] = useState<Candidate[] | null>(null);
  const task = useTask();
  async function decide(item: Candidate, decision: "duplicate" | "distinct") {
    await api(`/ai/jobs/${job.id}/duplicates`, "POST", {
      expected_version: job.version,
      target_id: item.job.id,
      target_version: item.job.version,
      decision,
      reason: t("Comparison confirmed by user in interface."),
      review_confirmed: true,
    });
    setItems(
      (previous) =>
        previous?.filter((candidate) => candidate.job.id !== item.job.id) ?? [],
    );
    if (decision === "duplicate") saved();
  }
  return (
    <section className="panel ai-panel">
      <h2>{t("Possible duplicates")}</h2>
      <p>
        {t(
          "Compares text and embeddings already available, without new AI call. A confirmation archives this job and preserves the other as reference; history is maintained.",
        )}
      </p>
      <button
        disabled={task.busy}
        onClick={() =>
          void task.run(async () => {
            setItems(
              (
                await api<{
                  items: Candidate[];
                }>(`/ai/jobs/${job.id}/duplicates`)
              ).items,
            );
          }, t("Comparison completed."))
        }
      >
        {t("Compare with other jobs")}
      </button>
      {task.feedback}
      {items && !items.length && (
        <p>{t("No possible duplicates in this comparison.")}</p>
      )}
      {items?.map((item) => (
        <article key={item.job.id}>
          <h3>
            <a href={`#job/${item.job.id}`}>
              {item.job.title || t("Untitled job")}
            </a>
          </h3>
          <p>
            {item.job.company_name || t("Unknown company")} ·{" "}
            {item.job.location || t("Unknown location")}
          </p>
          <p>
            {t("Textual similarity: ")}
            {item.lexical_similarity.toFixed(3)}
            {t(" \u00B7 Semantic similarity: ")}
            {item.semantic_similarity?.toFixed(3) ?? t("Not indexed")}
          </p>
          {item.shared_identity && (
            <p>{t("There is a common source reference.")}</p>
          )}
          {!!item.conflicts.length && (
            <p>
              {t(
                "Company or location differ. Review fields before confirming.",
              )}
            </p>
          )}
          <details>
            <summary>{t("View text to compare")}</summary>
            <p className="preserve">{item.job.raw_text}</p>
          </details>
          <div className="actions">
            <button
              disabled={task.busy || !!item.conflicts.length || job.archived}
              onClick={() =>
                void task.run(
                  () => decide(item, "duplicate"),
                  t("Duplicate confirmed; this job has been archived."),
                )
              }
            >
              {t("Confirm duplicate and archive this job")}
            </button>
            <button
              disabled={task.busy}
              onClick={() =>
                void task.run(
                  () => decide(item, "distinct"),
                  t("Distinct jobs recorded."),
                )
              }
            >
              {t("They are distinct vacancies")}
            </button>
          </div>
        </article>
      ))}
    </section>
  );
}

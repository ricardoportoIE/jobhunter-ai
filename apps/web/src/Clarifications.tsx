import { t, systemMessage } from "./i18n";
import { useEffect, useState } from "react";
import { api } from "./api";
import { outcomes, type Assessment, type Job, type Profile } from "./types";
export type Clarification = {
  key: string;
  code: string;
  message: string;
  requirement_id: string | null;
  requires_assessment_change?: boolean;
  alternatives?: {
    run_id: string;
    model: string;
    status: string;
    reason: string;
  }[];
};
export type Resolution = {
  key: string;
  note: string;
  source_reference: string;
};
export function ClarificationList({ issues }: { issues: Clarification[] }) {
  return (
    <>
      {issues.map((issue) => (
        <article className="record" key={issue.key}>
          <p>{systemMessage(issue.message)}</p>
          {issue.alternatives?.map((answer) => (
            <blockquote key={answer.run_id}>
              <strong>
                {answer.model} · {outcomes[answer.status]}
              </strong>
              <p>{answer.reason}</p>
            </blockquote>
          ))}
        </article>
      ))}
    </>
  );
}
export default function Clarifications({
  job,
  profile,
  assessments,
  revision,
  resolutions,
  change,
}: {
  job: Job;
  profile: Profile;
  assessments: Assessment[];
  revision: number;
  resolutions: Resolution[];
  change: (value: Resolution[]) => void;
}) {
  const [issues, setIssues] = useState<Clarification[]>([]);
  const [error, setError] = useState("");
  const signature = JSON.stringify(
    assessments.map((a) => ({ ...a, reason: t("Review in progress") })),
  );
  useEffect(() => {
    let active = true;
    api<Clarification[]>(`/jobs/${job.id}/clarifications/preview`, "POST", {
      job_version: job.version,
      profile_version: profile.version,
      assessments: JSON.parse(signature),
    })
      .then((value) => {
        if (active) {
          setIssues(value);
          setError("");
        }
      })
      .catch((reason: Error) => {
        if (active) setError(reason.message);
      });
    return () => {
      active = false;
    };
  }, [job.id, job.version, profile.version, signature, revision]);
  function edit(key: string, update: Partial<Resolution>) {
    const previous = resolutions.find((r) => r.key === key) ?? {
      key,
      note: "",
      source_reference: "",
    };
    change([
      ...resolutions.filter(
        (r) => r.key !== key && issues.some((i) => i.key === r.key),
      ),
      { ...previous, ...update },
    ]);
  }
  return (
    <section className="ai-panel" aria-label={t("Clarifications")}>
      <h3>{t("Clarifications and discrepancies")}</h3>
      <p>
        {t(
          "A disagreement does not remove the job from scope. Record the source and conclusion before prioritising. A note does not establish that an unknown disqualifying requirement is met.",
        )}
      </p>
      {error && <p role="alert">{error}</p>}
      {!issues.length && !error && (
        <p>{t("No clarifications flagged in this review.")}</p>
      )}
      {issues.map((issue) => (
        <div key={issue.key}>
          <ClarificationList issues={[issue]} />
          {!issue.requires_assessment_change && (
            <>
              <label>
                {t("Review completion")}
                <textarea
                  minLength={20}
                  maxLength={3000}
                  value={
                    resolutions.find((r) => r.key === issue.key)?.note ?? ""
                  }
                  onChange={(event) =>
                    edit(issue.key, { note: event.target.value })
                  }
                />
              </label>
              <label>
                {t("Source or reference consulted")}
                <input
                  maxLength={2000}
                  value={
                    resolutions.find((r) => r.key === issue.key)
                      ?.source_reference ?? ""
                  }
                  onChange={(event) =>
                    edit(issue.key, { source_reference: event.target.value })
                  }
                />
              </label>
            </>
          )}
        </div>
      ))}
    </section>
  );
}

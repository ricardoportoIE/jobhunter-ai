import { useEffect, useState } from "react";
import { api } from "./api";
import { outcomes, type Assessment, type Job, type Profile } from "./types";

export type Clarification = {
  key: string;
  code: string;
  message: string;
  requirement_id: string | null;
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
          <p>{issue.message}</p>
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
    assessments.map((a) => ({ ...a, reason: "Revisão em curso" })),
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
    <section className="ai-panel" aria-label="Esclarecimentos">
      <h3>Esclarecimentos e divergências</h3>
      <p>
        Uma divergência não elimina a vaga do escopo. Registre a fonte e a
        conclusão antes de priorizar. Uma nota não comprova um requisito
        eliminatório ainda desconhecido.
      </p>
      {error && <p role="alert">{error}</p>}
      {!issues.length && !error && (
        <p>Nenhum esclarecimento sinalizado nesta revisão.</p>
      )}
      {issues.map((issue) => (
        <div key={issue.key}>
          <ClarificationList issues={[issue]} />
          {issue.code !== "DECISIVE_INFORMATION_MISSING" && (
            <>
              <label>
                Conclusão da revisão
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
                Fonte ou referência consultada
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

import { useState } from "react";
import { api } from "./api";
import {
  outcomes,
  type Assessment,
  type Fact,
  type Job,
  type Profile,
} from "./types";
import { useTask } from "./useTask";

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
}: {
  job: Job;
  profile: Profile;
  facts: Fact[];
  apply: (assessments: Assessment[], run: string | null) => void;
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const [consent, setConsent] = useState(false);
  const [suggestion, setSuggestion] = useState<Suggestion | null>(null);
  const task = useTask();
  const available = facts.filter(
    (f) =>
      f.status === "verified" &&
      f.allowed_uses.includes("matching") &&
      f.sensitivity !== "sensitive",
  );
  return (
    <section className="ai-panel">
      <h3>Sugestões com evidências</h3>
      <p>
        Selecione os fatos que a IA pode avaliar. Serão enviados à OpenAI os
        requisitos, as afirmações selecionadas e os trechos das suas evidências.
        Dados marcados como sensíveis são excluídos; nomes de arquivos e
        referências locais permanecem aqui.
      </p>
      <fieldset>
        <legend>Fatos autorizados para esta consulta</legend>
        {available.map((fact) => (
          <label className="check" key={fact.id}>
            <input
              type="checkbox"
              checked={selected.includes(fact.id)}
              disabled={
                task.busy ||
                (!selected.includes(fact.id) && selected.length >= 20)
              }
              onChange={(event) =>
                setSelected((previous) =>
                  event.target.checked
                    ? [...previous, fact.id]
                    : previous.filter((id) => id !== fact.id),
                )
              }
            />
            {fact.claim}
          </label>
        ))}
        {!available.length && (
          <p>
            Nenhum fato elegível disponível. Registre evidências e publique o
            perfil.
          </p>
        )}
      </fieldset>
      <label className="check">
        <input
          type="checkbox"
          checked={consent}
          onChange={(event) => setConsent(event.target.checked)}
        />
        Autorizo o envio dos fatos selecionados e seus trechos de evidência à
        OpenAI.
      </label>
      <button
        disabled={task.busy || !consent}
        onClick={() =>
          void task.run(async () => {
            setSuggestion(
              await api<Suggestion>(`/ai/jobs/${job.id}/suggest`, "POST", {
                job_version: job.version,
                profile_version: profile.version,
                fact_ids: selected,
                external_processing_confirmed: true,
              }),
            );
          }, "Sugestões prontas para revisão.")
        }
      >
        {task.busy ? "Avaliando…" : "Sugerir avaliações com IA"}
      </button>
      {task.feedback}
      {suggestion && (
        <>
          {suggestion.stale && (
            <p role="alert">
              A vaga ou o perfil mudou. Gere uma nova sugestão.
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
                Confiança declarada: {Math.round(item.confidence * 100)}% (não
                calibrada)
              </small>
              {item.citations.map((citation, index) => (
                <details key={index}>
                  <summary>Conferir fato e evidência</summary>
                  <p>Fato: {citation.fact_quote}</p>
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
            Preencher avaliações para minha revisão
          </button>
        </>
      )}
    </section>
  );
}

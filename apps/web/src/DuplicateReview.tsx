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
      reason: "Comparação confirmada pelo utilizador na interface.",
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
      <h2>Possíveis duplicados</h2>
      <p>
        Compara texto e embeddings já disponíveis, sem nova chamada à IA. Uma
        confirmação arquiva esta vaga e preserva a outra como referência; o
        histórico é mantido.
      </p>
      <button
        disabled={task.busy}
        onClick={() =>
          void task.run(async () => {
            setItems(
              (
                await api<{ items: Candidate[] }>(
                  `/ai/jobs/${job.id}/duplicates`,
                )
              ).items,
            );
          }, "Comparação concluída.")
        }
      >
        Comparar com outras vagas
      </button>
      {task.feedback}
      {items && !items.length && (
        <p>Nenhum possível duplicado nesta comparação.</p>
      )}
      {items?.map((item) => (
        <article key={item.job.id}>
          <h3>
            <a href={`#job/${item.job.id}`}>
              {item.job.title || "Vaga sem título"}
            </a>
          </h3>
          <p>
            {item.job.company_name || "Empresa desconhecida"} ·{" "}
            {item.job.location || "Local desconhecido"}
          </p>
          <p>
            Similaridade textual: {item.lexical_similarity.toFixed(3)} ·
            Semântica: {item.semantic_similarity?.toFixed(3) ?? "Não indexada"}
          </p>
          {item.shared_identity && <p>Há uma referência de origem em comum.</p>}
          {!!item.conflicts.length && (
            <p>
              Empresa ou localidade divergem. Revise os campos antes de
              confirmar.
            </p>
          )}
          <details>
            <summary>Ver texto para comparar</summary>
            <p className="preserve">{item.job.raw_text}</p>
          </details>
          <div className="actions">
            <button
              disabled={task.busy || !!item.conflicts.length || job.archived}
              onClick={() =>
                void task.run(
                  () => decide(item, "duplicate"),
                  "Duplicado confirmado; esta vaga foi arquivada.",
                )
              }
            >
              Confirmar duplicada e arquivar esta vaga
            </button>
            <button
              disabled={task.busy}
              onClick={() =>
                void task.run(
                  () => decide(item, "distinct"),
                  "Vagas distintas registradas.",
                )
              }
            >
              São vagas distintas
            </button>
          </div>
        </article>
      ))}
    </section>
  );
}

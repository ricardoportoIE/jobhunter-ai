import { api } from "./api";
import type { Match } from "./types";
import { useTask } from "./useTask";

export default function ShortlistButton({ match }: { match: Match }) {
  const task = useTask();
  return (
    <div className="review-callout">
      <p>
        Adicionar à shortlist registra seu interesse. A decisão de candidatura
        continua sob seu controle.
      </p>
      {task.feedback}
      <button
        className="primary"
        disabled={task.busy || match.stale}
        onClick={() => {
          void task.run(async () => {
            await api("/applications", "POST", {
              job_id: match.job_id,
              match_id: match.id,
            });
          }, "Adicionada à shortlist.");
        }}
      >
        Adicionar à shortlist
      </button>{" "}
      <a href="#tracker">Ver candidaturas →</a>
    </div>
  );
}

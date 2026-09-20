import { useEffect, useState } from "react";
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
    citations: { url: string; title: string; start: number; end: number }[];
  };
};
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
      <h2>Consultar informação pública atualizada</h2>
      <p>
        Envie somente uma pergunta pública, sem dados pessoais. A busca usa os
        domínios indicados e retorna fontes para sua conferência. Os fatos do
        perfil e a compatibilidade permanecem sujeitos à revisão.
      </p>
      <label>
        Pergunta pública
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
        Domínios das fontes, separados por vírgulas
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
        Autorizo enviar esta pergunta pública à OpenAI e à busca web.
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
          }, "Pesquisa disponível para conferência.")
        }
      >
        {task.busy ? "Pesquisando…" : "Pesquisar fontes públicas"}
      </button>
      {task.feedback}
      {error && <p role="alert">{error}</p>}
      {history.map((item) => (
        <details key={item.run_id} open>
          <summary>{item.result.question}</summary>
          <p>
            Consultado em{" "}
            {new Date(item.result.retrieved_at).toLocaleString("pt-PT")} ·
            Conferência humana necessária
          </p>
          {(item.stale || Date.parse(item.result.refresh_after) <= now) && (
            <p role="status">
              Consulta antiga: pesquise novamente antes de usar informação
              decisiva.
            </p>
          )}
          <p className="preserve">{item.result.answer}</p>
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

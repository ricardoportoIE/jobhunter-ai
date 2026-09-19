import { useEffect, useState } from "react";
import { api } from "./api";
import type { Job } from "./types";
import { useTask } from "./useTask";
import { ErrorState, Loading } from "./ui";

export type AiStatus = {
  configured: boolean;
  model: string;
  budget: {
    spent_eur: string;
    reserved_eur: string;
    limit_eur: string;
    unreconciled: boolean;
    alerts: number[];
  };
};
type Citation = { quote: string; confidence: number };
export type Extraction = {
  run_id: string;
  stale?: boolean;
  result: {
    fields: Record<string, unknown>;
    citations: Record<string, Citation>;
    requirements: { text: string; citation: Citation }[];
    risk_flags: string[];
    job_version: number;
  };
};
const labels: Record<string, string> = {
  title: "Título",
  company_name: "Empresa",
  location: "Localidade",
  country: "País",
  work_mode: "Modalidade",
  employment_type: "Contrato",
  seniority: "Nível",
  work_authorisation: "Autorização",
  sponsorship: "Sponsorship",
  salary: "Salário",
};
function Quote({ citation }: { citation?: Citation }) {
  return citation ? (
    <>
      <blockquote>{citation.quote}</blockquote>
      <small>
        Confiança declarada pela IA: {Math.round(citation.confidence * 100)}%
        {citation.confidence < 0.75 ? " · Conferência prioritária" : ""}
      </small>
    </>
  ) : (
    <small>Sem informação no anúncio.</small>
  );
}
export function AiJobTools({ job, saved }: { job: Job; saved: () => void }) {
  const [extraction, setExtraction] = useState<Extraction | null>(null);
  const task = useTask();
  useEffect(() => {
    let active = true;
    api<Extraction | null>(`/ai/jobs/${job.id}/extraction`)
      .then((result) => {
        if (active) setExtraction(result);
      })
      .catch(() => {
        /* Optional history; explicit actions report errors below. */
      });
    return () => {
      active = false;
    };
  }, [job.id, job.version]);
  const stale = extraction && extraction.result.job_version !== job.version;
  return (
    <section className="panel ai-panel">
      <p className="eyebrow">ASSISTENTE DE LEITURA</p>
      <h2>Extrair campos com IA</h2>
      <p>
        Envia o texto desta vaga à OpenAI. A extração fica como sugestão até
        você revisar. Confiança indica a estimativa do modelo; não é uma
        probabilidade validada.
      </p>
      <button
        disabled={task.busy}
        onClick={() =>
          void task.run(async () => {
            setExtraction(
              await api<Extraction>(`/ai/jobs/${job.id}/parse`, "POST", {
                expected_version: job.version,
              }),
            );
          }, "Extração disponível para conferência.")
        }
      >
        {task.busy ? "Processando…" : "Extrair com IA"}
      </button>
      {task.feedback}
      {extraction && (
        <details open>
          <summary>Conferir sugestões e trechos de origem</summary>
          {stale && (
            <p role="status">
              Esta extração corresponde a uma versão anterior da vaga.
            </p>
          )}
          <div className="ai-fields">
            {Object.entries(extraction.result.fields).map(([name, value]) => (
              <article key={name}>
                <h3>{labels[name] || name}</h3>
                <p>
                  {value === null
                    ? "Desconhecido"
                    : typeof value === "object"
                      ? Object.entries(value as Record<string, unknown>)
                          .filter(([, v]) => v !== null)
                          .map(([k, v]) => `${k}: ${String(v)}`)
                          .join(" · ")
                      : String(value)}
                </p>
                <Quote citation={extraction.result.citations[name]} />
              </article>
            ))}
          </div>
          <h3>Requisitos sugeridos</h3>
          {extraction.result.requirements.map((item, index) => (
            <article key={index}>
              <p>
                <strong>{item.text}</strong>
              </p>
              <Quote citation={item.citation} />
            </article>
          ))}
          {extraction.result.risk_flags.map((flag) => (
            <p key={flag}>{flag}</p>
          ))}
          <button
            disabled={task.busy || !!stale}
            onClick={() =>
              void task.run(async () => {
                await api(`/ai/jobs/${job.id}/draft`, "POST", {
                  expected_version: job.version,
                  run_id: extraction.run_id,
                });
                saved();
              }, "Rascunho preenchido. Revise os campos abaixo e confirme a revisão.")
            }
          >
            Preencher rascunho para revisão
          </button>
        </details>
      )}
    </section>
  );
}

type Run = {
  id: string;
  operation: string;
  model: string;
  status: string;
  actual_eur: string | null;
  reserved_eur: string;
  input_tokens: number | null;
  output_tokens: number | null;
  latency_ms: number | null;
  error_code: string | null;
};
export function AiActivity() {
  const [data, setData] = useState<{ status: AiStatus; runs: Run[] } | null>(
    null,
  );
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    let active = true;
    Promise.all([api<AiStatus>("/ai/status"), api<Run[]>("/ai/runs")])
      .then(([status, runs]) => {
        if (active) {
          setData({ status, runs });
          setError("");
        }
      })
      .catch((reason: Error) => {
        if (active) setError(reason.message);
      });
    return () => {
      active = false;
    };
  }, [refresh]);
  if (error)
    return <ErrorState error={error} retry={() => setRefresh(refresh + 1)} />;
  if (!data) return <Loading />;
  const { status, runs } = data;
  return (
    <>
      <p className="eyebrow">CONTROLE DE USO</p>
      <h1>Atividade de IA</h1>
      <section className="panel">
        <p>
          {status.configured
            ? "OpenAI configurada"
            : "Chave ainda não configurada"}{" "}
          · {status.model}
        </p>
        <h2>Orçamento mensal</h2>
        <p>
          Consumo contabilizado: €{Number(status.budget.spent_eur).toFixed(4)} ·
          Reservado: €{Number(status.budget.reserved_eur).toFixed(4)} · Limite:
          €{status.budget.limit_eur}
        </p>
        <p>
          Estimativa conservadora do projeto; não é a fatura da conta. O
          controle combinado também preserva €15 para AWS dentro do teto de €25.
        </p>
        {status.budget.alerts.map((level) => (
          <p key={level} role="status">
            Uso de IA atingiu {level}% do limite.
          </p>
        ))}
        {status.budget.unreconciled && (
          <p role="alert">
            Novas chamadas bloqueadas: há custo desconhecido. Confira o uso no
            provedor e reconcilie pela administração local.
          </p>
        )}
        <button onClick={() => setRefresh(refresh + 1)}>
          Atualizar atividade
        </button>
      </section>
      <h2>Últimas execuções</h2>
      {!runs.length && <p>Nenhuma chamada realizada.</p>}
      {runs.map((run) => (
        <article className="panel" key={run.id}>
          <h3>
            {run.operation} · {run.status}
          </h3>
          <p>{run.model}</p>
          <p>
            €{Number(run.actual_eur ?? run.reserved_eur).toFixed(6)}
            {run.actual_eur === null ? " reservados" : " contabilizados"} ·
            {run.input_tokens ?? "?"} tokens de entrada ·{" "}
            {run.output_tokens ?? "?"} de saída ·{run.latency_ms ?? "?"} ms
          </p>
          {run.error_code && <p>{run.error_code}</p>}
          <small>Execução: {run.id}</small>
        </article>
      ))}
    </>
  );
}

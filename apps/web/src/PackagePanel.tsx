import { useEffect, useState } from "react";
import { api } from "./api";
import type { Evidence, Fact, Job, Profile } from "./types";
import { useTask } from "./useTask";
import { useAiTask } from "./useAiTask";

type Claim = {
  text: string;
  fact_id: string;
  category: string;
  evidence_ids: string[];
};
type Answer = {
  question_index: number;
  question: string;
  classification: string;
  text: string;
  source: string;
};
type Selection = {
  cv_fact_ids: string[];
  letter_fact_ids: string[];
  focus: { requirement_id: string; fact_ids: string[]; explanation: string }[];
  risks: string[];
  interview_points: string[];
};
type Strategy = {
  id: string;
  version: number;
  status: string;
  stale?: boolean;
  selection: Selection;
  snapshot: {
    facts: Fact[];
    evidence: Evidence[];
    job: Job;
    contact_lines: string[];
  };
};
type Package = Strategy & {
  content_hash: string;
  manual_answers: Record<string, string>;
  validation: {
    valid: boolean;
    errors: string[];
    warnings: string[];
    all_claims_traceable: boolean;
  };
  content: {
    name: string;
    job_title: string;
    company_name: string;
    contact_lines: string[];
    cv: Claim[];
    cover_letter: Claim[];
    answers: Answer[];
  };
  review: { note: string } | null;
};
const statusLabel: Record<string, string> = {
  NEEDS_REVIEW: "Aguardando revisão",
  APPROVED: "Aprovado",
  REJECTED: "Rejeitado",
};
const answerLabel: Record<string, string> = {
  SENSITIVE: "Sensível — revisão específica",
  BLOCKED: "Sem evidência — resposta pendente",
  REVIEW_REQUIRED: "Revisão necessária",
  AUTO_APPROVABLE: "Baseada em fato aprovado — conferir",
};
const errorLabel: Record<string, string> = {
  UNANSWERED_QUESTIONS: "Há perguntas sem resposta.",
  CONTENT_NOT_REPRODUCIBLE: "Conteúdo não corresponde às fontes.",
  UNSUPPORTED_CONTROL_CHARACTERS: "Corrija caracteres inválidos nos fatos.",
};

export default function PackagePanel({
  job,
  profile,
  facts,
}: {
  job: Job;
  profile: Profile;
  facts: Fact[];
}) {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [packages, setPackages] = useState<Package[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [questions, setQuestions] = useState("");
  const [contacts, setContacts] = useState("");
  const [useAi, setUseAi] = useState(true);
  const [consent, setConsent] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const task = useAiTask(!useAi || consent);
  useEffect(() => {
    let active = true;
    Promise.all([
      api<Strategy[]>(`/jobs/${job.id}/strategies`),
      api<Package[]>(`/jobs/${job.id}/packages`),
    ])
      .then(([s, p]) => {
        if (active) {
          setStrategies(s);
          setPackages(p);
          setLoadError("");
        }
      })
      .catch((e: Error) => {
        if (active) setLoadError(e.message);
      });
    return () => {
      active = false;
    };
  }, [job.id, job.version, profile.version, refresh]);
  const available = facts.filter(
    (f) =>
      f.status === "verified" &&
      f.sensitivity !== "sensitive" &&
      f.allowed_uses.some((u) =>
        ["cv", "cover_letter", "application_form"].includes(u),
      ),
  );
  const ready =
    profile.status === "reviewed" &&
    job.status !== "DISCOVERED" &&
    !job.archived;
  const reload = () => setRefresh((r) => r + 1);
  return (
    <section className="package-workspace">
      <div className="panel">
        <h2>Preparar candidatura</h2>
        <p>
          Escolha as evidências, revise a estratégia e aprove o pacote antes de
          baixar. Nenhuma candidatura é enviada.
        </p>
        {!ready && (
          <p role="alert">
            Publique o perfil e revise uma vaga ativa para começar.
          </p>
        )}
        {!profile.display_name && (
          <p role="alert">Preencha seu nome na página de perfil.</p>
        )}
        {loadError && (
          <p role="alert">
            {loadError} <button onClick={reload}>Atualizar pacotes</button>
          </p>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void task.run(async (headers) => {
              await api<Strategy>(
                `/jobs/${job.id}/strategy`,
                "POST",
                {
                  job_version: job.version,
                  profile_version: profile.version,
                  fact_ids: selected,
                  questions: questions
                    .split("\n")
                    .map((s) => s.trim())
                    .filter(Boolean),
                  contact_lines: contacts
                    .split("\n")
                    .map((s) => s.trim())
                    .filter(Boolean),
                  use_ai: useAi,
                  external_processing_confirmed: consent,
                },
                headers,
              );
              reload();
            }, "Estratégia preparada para revisão.");
          }}
        >
          <fieldset>
            <legend>Fatos autorizados para documentos</legend>
            {available.map((fact) => (
              <label className="check" key={fact.id}>
                <input
                  type="checkbox"
                  checked={selected.includes(fact.id)}
                  onChange={(e) => {
                    setSelected(
                      e.target.checked
                        ? [...selected, fact.id]
                        : selected.filter((id) => id !== fact.id),
                    );
                    setConsent(false);
                  }}
                />
                <span>
                  {fact.claim}
                  <small className="muted">
                    {" "}
                    Usos: {fact.allowed_uses.join(", ")}
                  </small>
                </span>
              </label>
            ))}
            {!available.length && (
              <p>Autorize fatos para CV e cover letter na base do candidato.</p>
            )}
          </fieldset>
          <label>
            Contato para os documentos — uma linha por item, até quatro
            <textarea
              value={contacts}
              onChange={(e) => setContacts(e.target.value)}
              placeholder="Email, telefone ou link profissional"
            />
          </label>
          <p className="muted">
            O contato fica local e será incluído nos documentos após sua
            revisão.
          </p>
          <label>
            Perguntas do formulário — uma por linha
            <textarea
              value={questions}
              onChange={(e) => {
                setQuestions(e.target.value);
                setConsent(false);
              }}
            />
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={useAi}
              onChange={(e) => {
                setUseAi(e.target.checked);
                setConsent(false);
              }}
            />
            Usar IA para priorizar fatos e apontar lacunas
          </label>
          {useAi && (
            <label className="check">
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
              />
              Autorizo enviar os fatos selecionados, suas evidências e perguntas
              à OpenAI.
            </label>
          )}
          {task.feedback}
          <button
            className="primary"
            disabled={
              task.busy || !ready || !selected.length || (useAi && !consent)
            }
          >
            Preparar estratégia
          </button>
        </form>
      </div>
      {strategies[0] && (
        <StrategyReview
          key={`${strategies[0].id}:${strategies[0].version}`}
          strategy={strategies[0]}
          job={job}
          saved={reload}
        />
      )}
      {packages.map((p) => (
        <PackageReview key={`${p.id}:${p.version}`} item={p} saved={reload} />
      ))}
    </section>
  );
}

function FactSelection({
  facts,
  cv,
  letter,
  setCv,
  setLetter,
}: {
  facts: Fact[];
  cv: string[];
  letter: string[];
  setCv: (v: string[]) => void;
  setLetter: (v: string[]) => void;
}) {
  return (
    <div className="package-columns">
      {[
        { use: "cv", label: "Fatos do CV", ids: cv, change: setCv },
        {
          use: "cover_letter",
          label: "Fatos da cover letter",
          ids: letter,
          change: setLetter,
        },
      ].map(({ use, label, ids, change }) => (
        <fieldset key={use}>
          <legend>{label}</legend>
          {facts
            .filter((f) => f.allowed_uses.includes(use))
            .map((f) => (
              <label className="check" key={f.id}>
                <input
                  type="checkbox"
                  checked={ids.includes(f.id)}
                  onChange={(e) =>
                    change(
                      e.target.checked
                        ? [...ids, f.id]
                        : ids.filter((id) => id !== f.id),
                    )
                  }
                />
                {f.claim}
              </label>
            ))}
          <ol>
            {ids.map((id, index) => (
              <li key={id}>
                {facts.find((f) => f.id === id)?.claim}
                <button
                  type="button"
                  disabled={index === 0}
                  aria-label={`Mover fato ${index + 1} para cima em ${label}`}
                  onClick={() => {
                    const next = [...ids];
                    [next[index - 1], next[index]] = [
                      next[index]!,
                      next[index - 1]!,
                    ];
                    change(next);
                  }}
                >
                  ↑
                </button>
              </li>
            ))}
          </ol>
        </fieldset>
      ))}
    </div>
  );
}

function StrategyReview({
  strategy,
  job,
  saved,
}: {
  strategy: Strategy;
  job: Job;
  saved: () => void;
}) {
  const task = useTask();
  const [cv, setCv] = useState(strategy.selection.cv_fact_ids);
  const [letter, setLetter] = useState(strategy.selection.letter_fact_ids);
  const [confirmed, setConfirmed] = useState(false);
  return (
    <section className="panel">
      <h2>Revisar estratégia</h2>
      <p>
        {statusLabel[strategy.status]} · versão {strategy.version}
      </p>
      {strategy.stale && (
        <p role="alert">
          Estratégia desatualizada. Prepare uma nova com as fontes atuais.
        </p>
      )}
      {strategy.selection.focus.map((f) => (
        <article className="record" key={f.requirement_id}>
          <h3>
            {
              strategy.snapshot.job.requirements.find(
                (r) => r.id === f.requirement_id,
              )?.text
            }
          </h3>
          <p>{f.explanation}</p>
          {f.fact_ids.map((id) => (
            <p key={id}>
              {strategy.snapshot.facts.find((fact) => fact.id === id)?.claim}
            </p>
          ))}
        </article>
      ))}
      {strategy.selection.risks.map((r, i) => (
        <p className="muted" key={i}>
          {r}
        </p>
      ))}
      {strategy.selection.interview_points.length > 0 && (
        <details>
          <summary>Pontos para preparar a entrevista</summary>
          <ul>
            {strategy.selection.interview_points.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </details>
      )}
      <p>
        Contato:{" "}
        {strategy.snapshot.contact_lines.join(" · ") || "não informado"}
      </p>
      <FactSelection
        facts={strategy.snapshot.facts}
        cv={cv}
        letter={letter}
        setCv={(v) => {
          setCv(v);
          setConfirmed(false);
        }}
        setLetter={(v) => {
          setLetter(v);
          setConfirmed(false);
        }}
      />
      <label className="check">
        <input
          type="checkbox"
          checked={confirmed}
          onChange={(e) => setConfirmed(e.target.checked)}
        />
        Revisei a seleção, a estratégia e o contato dos documentos.
      </label>
      {task.feedback}
      <div className="actions">
        <button
          disabled={
            task.busy ||
            strategy.stale ||
            !confirmed ||
            !cv.length ||
            !letter.length
          }
          onClick={() =>
            void task.run(async () => {
              await api(`/strategies/${strategy.id}/approve`, "POST", {
                expected_version: strategy.version,
                cv_fact_ids: cv,
                letter_fact_ids: letter,
                review_confirmed: true,
              });
              saved();
            })
          }
        >
          Aprovar estratégia
        </button>
        <button
          className="primary"
          disabled={
            task.busy ||
            strategy.stale ||
            strategy.status !== "APPROVED" ||
            JSON.stringify(cv) !==
              JSON.stringify(strategy.selection.cv_fact_ids) ||
            JSON.stringify(letter) !==
              JSON.stringify(strategy.selection.letter_fact_ids)
          }
          onClick={() =>
            void task.run(async () => {
              await api(`/jobs/${job.id}/generate-package`, "POST", {
                strategy_id: strategy.id,
                strategy_version: strategy.version,
              });
              saved();
            }, "Pacote gerado para revisão.")
          }
        >
          Gerar pacote
        </button>
      </div>
    </section>
  );
}

function PackageReview({ item, saved }: { item: Package; saved: () => void }) {
  const task = useTask();
  const [cv, setCv] = useState(item.selection.cv_fact_ids);
  const [letter, setLetter] = useState(item.selection.letter_fact_ids);
  const [answers, setAnswers] = useState(item.manual_answers);
  const [attest, setAttest] = useState(false);
  const [reviewed, setReviewed] = useState(false);
  const [sensitiveReviewed, setSensitiveReviewed] = useState(false);
  const [note, setNote] = useState("");
  const [difference, setDifference] = useState("");
  const [history, setHistory] = useState<{ version: number; status: string }[]>(
    [],
  );
  const [fromVersion, setFromVersion] = useState("1");
  const sensitive = item.content.answers.some(
    (a) => a.classification === "SENSITIVE",
  );
  const dirty =
    JSON.stringify(cv) !== JSON.stringify(item.selection.cv_fact_ids) ||
    JSON.stringify(letter) !== JSON.stringify(item.selection.letter_fact_ids) ||
    JSON.stringify(answers) !== JSON.stringify(item.manual_answers);
  const actReview = (decision: string) =>
    void task.run(async () => {
      await api(`/packages/${item.id}/review`, "POST", {
        expected_version: item.version,
        decision,
        review_confirmed: true,
        sensitive_review_confirmed: sensitiveReviewed,
        note,
      });
      saved();
    });
  return (
    <section className="panel package-review">
      <h2>Revisar pacote</h2>
      <p>
        {statusLabel[item.status]} · versão {item.version}
      </p>
      {item.stale && (
        <p role="alert">
          Fontes desatualizadas. Aprovação e downloads bloqueados; prepare uma
          nova estratégia.
        </p>
      )}
      <p>
        {item.validation.all_claims_traceable
          ? "Alegações vinculadas aos fatos aprovados."
          : "Há problemas de rastreabilidade."}{" "}
        Confira relevância, idioma e apresentação.
      </p>
      {item.validation.errors.map((e) => (
        <p role="alert" key={e}>
          {errorLabel[e] || e}
        </p>
      ))}
      <div className="package-columns">
        <section className="document-preview" aria-label="Prévia do CV">
          <h3>{item.content.name}</h3>
          <p>{item.content.contact_lines.join(" · ")}</p>
          <p>Application for {item.content.job_title}</p>
          {item.content.cv.map((claim) => (
            <p key={claim.fact_id}>{claim.text}</p>
          ))}
        </section>
        <section
          className="document-preview"
          aria-label="Prévia da cover letter"
        >
          <h3>Cover letter</h3>
          <p>Dear Hiring Team,</p>
          <p>
            I am applying for the {item.content.job_title} position at{" "}
            {item.content.company_name}.
          </p>
          <p>The following background is relevant to my application:</p>
          {item.content.cover_letter.map((claim) => (
            <p key={claim.fact_id}>{claim.text}</p>
          ))}
          <p>
            I would welcome the opportunity to discuss how this background
            relates to the role.
          </p>
          <p>
            Yours faithfully,
            <br />
            {item.content.name}
          </p>
        </section>
      </div>
      <details>
        <summary>Conferir origem de cada alegação</summary>
        {item.snapshot.facts.map((f) => (
          <article className="record" key={f.id}>
            <p>{f.claim}</p>
            <small>Fato versão {f.version}</small>
            {f.evidence_ids.map((id) => (
              <p className="preserve" key={id}>
                {item.snapshot.evidence.find((e) => e.id === id)?.content}
              </p>
            ))}
          </article>
        ))}
      </details>
      <details>
        <summary>Ajustar seleção e ordem dos documentos</summary>
        <p>
          Para alterar datas, cargos ou alegações, corrija a base do candidato e
          gere outra estratégia.
        </p>
        <FactSelection
          facts={item.snapshot.facts}
          cv={cv}
          letter={letter}
          setCv={(v) => {
            setCv(v);
            setReviewed(false);
          }}
          setLetter={(v) => {
            setLetter(v);
            setReviewed(false);
          }}
        />
      </details>
      {item.content.answers.length > 0 && (
        <section>
          <h3>Respostas do formulário</h3>
          {item.content.answers.map((a) => (
            <label key={a.question_index}>
              {a.question}
              <small className="muted">{answerLabel[a.classification]}</small>
              <textarea
                aria-label={`Resposta: ${a.question}`}
                value={answers[String(a.question_index)] ?? a.text}
                onChange={(e) => {
                  setAnswers({
                    ...answers,
                    [String(a.question_index)]: e.target.value,
                  });
                  setReviewed(false);
                  setAttest(false);
                  setSensitiveReviewed(false);
                }}
              />
            </label>
          ))}
          <label className="check">
            <input
              type="checkbox"
              checked={attest}
              onChange={(e) => setAttest(e.target.checked)}
            />
            Declaro que as respostas manuais são verdadeiras e autorizo
            incluí-las neste pacote.
          </label>
        </section>
      )}
      <div className="actions">
        <button
          disabled={
            task.busy ||
            item.stale ||
            !dirty ||
            !cv.length ||
            !letter.length ||
            (Object.values(answers).some((v) => v.trim()) && !attest)
          }
          onClick={() =>
            void task.run(async () => {
              await api(`/packages/${item.id}`, "PATCH", {
                expected_version: item.version,
                cv_fact_ids: cv,
                letter_fact_ids: letter,
                review_confirmed: true,
                manual_answers: Object.fromEntries(
                  Object.entries(answers).filter(([, v]) => v.trim()),
                ),
                attest_answers: attest,
              });
              saved();
            }, "Nova versão salva; revise antes de aprovar.")
          }
        >
          Salvar nova versão
        </button>
        <button
          onClick={() =>
            void task.run(async () => {
              setHistory(await api(`/packages/${item.id}/history`));
            }, "Histórico carregado.")
          }
        >
          Ver histórico e diferenças
        </button>
      </div>
      {history.length > 0 && (
        <div>
          <p>
            {history
              .map((h) => `v${h.version}: ${statusLabel[h.status]}`)
              .join(" · ")}
          </p>
          {history.some((h) => h.version < item.version) && (
            <>
              <label>
                Comparar com versão
                <select
                  value={fromVersion}
                  onChange={(e) => setFromVersion(e.target.value)}
                >
                  {history
                    .filter((h) => h.version < item.version)
                    .map((h) => (
                      <option key={h.version} value={h.version}>
                        Versão {h.version}
                      </option>
                    ))}
                </select>
              </label>
              <button
                onClick={() =>
                  void task.run(async () => {
                    const result = await api<{ diff: string }>(
                      `/packages/${item.id}/diff?from_version=${fromVersion}`,
                    );
                    setDifference(
                      result.diff || "Nenhuma diferença no conteúdo.",
                    );
                  })
                }
              >
                Mostrar diferenças
              </button>
              <pre className="package-diff">{difference}</pre>
            </>
          )}
        </div>
      )}
      <label>
        Nota da revisão
        <textarea value={note} onChange={(e) => setNote(e.target.value)} />
      </label>
      <label className="check">
        <input
          type="checkbox"
          checked={reviewed}
          onChange={(e) => setReviewed(e.target.checked)}
        />
        Conferi os fatos, o inglês e a apresentação desta versão.
      </label>
      {sensitive && (
        <label className="check">
          <input
            type="checkbox"
            checked={sensitiveReviewed}
            onChange={(e) => setSensitiveReviewed(e.target.checked)}
          />
          Revisei especificamente salário, autorização, disponibilidade e demais
          respostas sensíveis presentes.
        </label>
      )}
      {dirty && (
        <p role="status">Salve as alterações antes de revisar esta versão.</p>
      )}
      {task.feedback}
      <div className="actions">
        <button
          className="primary"
          disabled={
            task.busy ||
            item.stale ||
            dirty ||
            !reviewed ||
            !item.validation.valid ||
            (sensitive && !sensitiveReviewed)
          }
          onClick={() => actReview("approve")}
        >
          Aprovar pacote para download
        </button>
        <button
          disabled={task.busy || item.stale || dirty || !reviewed}
          onClick={() => actReview("reject")}
        >
          Rejeitar pacote
        </button>
      </div>
      {item.review?.note && <p>Última revisão: {item.review.note}</p>}
      {item.status === "APPROVED" && !item.stale && !dirty && (
        <nav className="actions" aria-label="Downloads do pacote">
          {[
            "cv.docx",
            "cv.pdf",
            "cover-letter.docx",
            "cover-letter.pdf",
            "answers.json",
            "package.json",
            "bundle.zip",
          ].map((name) => (
            <a
              key={name}
              href={`/api/v1/packages/${item.id}/download/${name}?expected_version=${item.version}`}
            >
              {name === "bundle.zip" ? "Baixar pacote ZIP" : name}
            </a>
          ))}
        </nav>
      )}
    </section>
  );
}

import { t, localisedLabels } from "./i18n";
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
  focus: {
    requirement_id: string;
    fact_ids: string[];
    explanation: string;
  }[];
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
  review: {
    note: string;
  } | null;
};
const statusLabel: Record<string, string> = localisedLabels({
  NEEDS_REVIEW: "Awaiting review",
  APPROVED: "Approved",
  REJECTED: "Rejected",
});
const answerLabel: Record<string, string> = localisedLabels({
  SENSITIVE: "Sensitive \u2014 specific review",
  BLOCKED: "No evidence \u2014 response pending",
  REVIEW_REQUIRED: "Review required",
  AUTO_APPROVABLE: "Based on approved fact \u2014 verify",
});
const errorLabel: Record<string, string> = localisedLabels({
  UNANSWERED_QUESTIONS: "There are unanswered questions.",
  CONTENT_NOT_REPRODUCIBLE: "Content does not match sources.",
  UNSUPPORTED_CONTROL_CHARACTERS: "Correct invalid characters in facts.",
});
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
        <h2>{t("Prepare application")}</h2>
        <p>
          {t(
            "Choose the evidence, review the strategy and approve the package before downloading. No application is sent.",
          )}
        </p>
        {!ready && (
          <p role="alert">
            {t("Publish the profile and review an active vacancy to start.")}
          </p>
        )}
        {!profile.display_name && (
          <p role="alert">{t("Fill in your name on the profile page.")}</p>
        )}
        {loadError && (
          <p role="alert">
            {loadError} <button onClick={reload}>{t("Update packages")}</button>
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
            }, t("Strategy prepared for review."));
          }}
        >
          <fieldset>
            <legend>{t("Facts authorised for documents")}</legend>
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
                    {t("Uses: ")}
                    {fact.allowed_uses.join(", ")}
                  </small>
                </span>
              </label>
            ))}
            {!available.length && (
              <p>
                {t(
                  "Authorise facts for CV and cover letter in the candidate base.",
                )}
              </p>
            )}
          </fieldset>
          <label>
            {t("Contact for documents \u2014 one line per item, up to four")}
            <textarea
              value={contacts}
              onChange={(e) => setContacts(e.target.value)}
              placeholder={t("Email, phone or professional link")}
            />
          </label>
          <p className="muted">
            {t(
              "The contact is local and will be included in documents after your review.",
            )}
          </p>
          <label>
            {t("Form questions \u2014 one per line")}
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
            {t("Use AI to prioritise facts and highlight gaps")}
          </label>
          {useAi && (
            <label className="check">
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
              />
              {t(
                "I authorise sending selected facts, their evidence and questions to OpenAI.",
              )}
            </label>
          )}
          {task.feedback}
          <button
            className="primary"
            disabled={
              task.busy || !ready || !selected.length || (useAi && !consent)
            }
          >
            {t("Prepare strategy")}
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
        { use: "cv", label: t("Facts from the CV"), ids: cv, change: setCv },
        {
          use: "cover_letter",
          label: t("Facts from the cover letter"),
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
                  aria-label={t("Move fact {0} up in {1}", [index + 1, label])}
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
      <h2>{t("Review strategy")}</h2>
      <p>
        {statusLabel[strategy.status]}
        {t(" \u00B7 version ")}
        {strategy.version}
      </p>
      {strategy.stale && (
        <p role="alert">
          {t("Outdated strategy. Prepare a new one with current sources.")}
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
          <summary>{t("Interview preparation points")}</summary>
          <ul>
            {strategy.selection.interview_points.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </details>
      )}
      <p>
        {t("Contact:")}{" "}
        {strategy.snapshot.contact_lines.join(" · ") || t("not informed")}
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
        {t("I reviewed the selection, strategy and document contact.")}
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
          {t("Approve strategy")}
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
            }, t("Package generated for review."))
          }
        >
          {t("Generate package")}
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
  const [history, setHistory] = useState<
    {
      version: number;
      status: string;
    }[]
  >([]);
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
      <h2>{t("Review package")}</h2>
      <p>
        {statusLabel[item.status]}
        {t(" \u00B7 version ")}
        {item.version}
      </p>
      {item.stale && (
        <p role="alert">
          {t(
            "Outdated sources. Approval and downloads blocked; prepare a new strategy.",
          )}
        </p>
      )}
      <p>
        {item.validation.all_claims_traceable
          ? t("Claims linked to approved facts.")
          : t("There are traceability issues.")}{" "}
        {t("Check relevance, language and presentation.")}
      </p>
      {item.validation.errors.map((e) => (
        <p role="alert" key={e}>
          {errorLabel[e] || e}
        </p>
      ))}
      <div className="package-columns">
        <section className="document-preview" aria-label={t("CV preview")}>
          <h3>{item.content.name}</h3>
          <p>{item.content.contact_lines.join(" · ")}</p>
          <p>Application for {item.content.job_title}</p>
          {item.content.cv.map((claim) => (
            <p key={claim.fact_id}>{claim.text}</p>
          ))}
        </section>
        <section
          className="document-preview"
          aria-label={t("Cover letter preview")}
        >
          <h3>{t("Cover letter")}</h3>
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
        <summary>{t("Check the source of each claim")}</summary>
        {item.snapshot.facts.map((f) => (
          <article className="record" key={f.id}>
            <p>{f.claim}</p>
            <small>
              {t("Fact version ")}
              {f.version}
            </small>
            {f.evidence_ids.map((id) => (
              <p className="preserve" key={id}>
                {item.snapshot.evidence.find((e) => e.id === id)?.content}
              </p>
            ))}
          </article>
        ))}
      </details>
      <details>
        <summary>{t("Adjust selection and order of documents")}</summary>
        <p>
          {t(
            "To change dates, roles or claims, correct the candidate base and generate another strategy.",
          )}
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
          <h3>{t("Form responses")}</h3>
          {item.content.answers.map((a) => (
            <label key={a.question_index}>
              {a.question}
              <small className="muted">{answerLabel[a.classification]}</small>
              <textarea
                aria-label={t("Answer: {0}", [a.question])}
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
            {t(
              "I declare that the manual answers are true and authorise their inclusion in this package.",
            )}
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
            }, t("New version saved; review before approval."))
          }
        >
          {t("Save new version")}
        </button>
        <button
          onClick={() =>
            void task.run(async () => {
              setHistory(await api(`/packages/${item.id}/history`));
            }, t("History loaded."))
          }
        >
          {t("View history and differences")}
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
                {t("Compare with version")}
                <select
                  value={fromVersion}
                  onChange={(e) => setFromVersion(e.target.value)}
                >
                  {history
                    .filter((h) => h.version < item.version)
                    .map((h) => (
                      <option key={h.version} value={h.version}>
                        {t("Version ")}
                        {h.version}
                      </option>
                    ))}
                </select>
              </label>
              <button
                onClick={() =>
                  void task.run(async () => {
                    const result = await api<{
                      diff: string;
                    }>(`/packages/${item.id}/diff?from_version=${fromVersion}`);
                    setDifference(
                      result.diff || t("No difference in content."),
                    );
                  })
                }
              >
                {t("Show differences")}
              </button>
              <pre className="package-diff">{difference}</pre>
            </>
          )}
        </div>
      )}
      <label>
        {t("Review note")}
        <textarea value={note} onChange={(e) => setNote(e.target.value)} />
      </label>
      <label className="check">
        <input
          type="checkbox"
          checked={reviewed}
          onChange={(e) => setReviewed(e.target.checked)}
        />
        {t(
          "I checked the facts, the English and the presentation of this version.",
        )}
      </label>
      {sensitive && (
        <label className="check">
          <input
            type="checkbox"
            checked={sensitiveReviewed}
            onChange={(e) => setSensitiveReviewed(e.target.checked)}
          />
          {t(
            "I specifically reviewed salary, authorisation, availability and other sensitive responses present.",
          )}
        </label>
      )}
      {dirty && (
        <p role="status">{t("Save changes before reviewing this version.")}</p>
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
          {t("Approve package for download")}
        </button>
        <button
          disabled={task.busy || item.stale || dirty || !reviewed}
          onClick={() => actReview("reject")}
        >
          {t("Reject package")}
        </button>
      </div>
      {item.review?.note && (
        <p>
          {t("Last review: ")}
          {item.review.note}
        </p>
      )}
      {item.status === "APPROVED" && !item.stale && !dirty && (
        <nav className="actions" aria-label={t("Package downloads")}>
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
              {name === "bundle.zip" ? t("Download ZIP package") : name}
            </a>
          ))}
        </nav>
      )}
    </section>
  );
}

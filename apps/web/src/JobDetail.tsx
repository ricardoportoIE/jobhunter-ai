import { t, systemMessage } from "./i18n";
import { useTask } from "./useTask";
import { AiJobTools } from "./AiTools";
import DuplicateReview from "./DuplicateReview";
import AiMatching from "./AiMatching";
import Clarifications, {
  ClarificationList,
  type Resolution,
} from "./Clarifications";
import ResearchPanel from "./ResearchPanel";
import PackagePanel from "./PackagePanel";
import { optional } from "./forms";
import { useEffect, useState } from "react";
import ShortlistButton from "./ShortlistButton";
import { api } from "./api";
import {
  categories,
  gates,
  outcomes,
  recommendations,
  reviewFlags,
  type Assessment,
  type Category,
  type Fact,
  type Job,
  type Match,
  type Profile,
  type Requirement,
} from "./types";
import { ErrorState, Field, Loading } from "./ui";
export default function JobDetail({
  id,
  profile,
  facts,
}: {
  id: string;
  profile: Profile;
  facts: Fact[];
}) {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [tab, setTab] = useState<"review" | "analyse" | "result" | "package">(
    "review",
  );
  const [match, setMatch] = useState<Match | null>(null);
  const [notice, setNotice] = useState("");
  const jobIdentity = job?.id;
  useEffect(() => {
    if (jobIdentity) document.getElementById("job-stage")?.focus();
  }, [tab, jobIdentity]);
  useEffect(() => {
    let active = true;
    Promise.all([
      api<Job>(`/jobs/${id}`),
      api<
        {
          id: string;
        }[]
      >(`/jobs/${id}/matches`),
    ])
      .then(async ([item, matches]) => {
        const latest = matches[0]
          ? await api<Match>(`/matches/${matches[0].id}`)
          : null;
        if (active) {
          setJob(item);
          setMatch(latest);
          setError("");
        }
      })
      .catch((reason: Error) => {
        if (active) setError(reason.message);
      });
    return () => {
      active = false;
    };
  }, [id, refresh, profile.version]);
  if (error)
    return <ErrorState error={error} retry={() => setRefresh(refresh + 1)} />;
  if (!job) return <Loading />;
  return (
    <>
      <a className="back" href="#inbox">
        {t("\u2190 Back to Inbox")}
      </a>
      <div className="page-heading">
        <div>
          <p className="eyebrow">
            {job.status}
            {t(" \u00B7 VERSION ")}
            {job.version}
          </p>
          <h1>{job.title || t("Review opportunity")}</h1>
          <p>
            {job.company_name || t("Company not provided")} ·{" "}
            {job.location || t("Location not provided")}
          </p>
        </div>
      </div>
      <nav className="tabs step-tabs" aria-label={t("Opportunity stages")}>
        <button
          aria-pressed={tab === "review"}
          onClick={() => setTab("review")}
        >
          {t("1. Review job")}
        </button>
        <button
          aria-pressed={tab === "analyse"}
          onClick={() => setTab("analyse")}
        >
          {t("2. Assess requirements")}
        </button>
        <button
          aria-pressed={tab === "result"}
          onClick={() => setTab("result")}
        >
          {t("3. Outcome and evidence")}
        </button>
        <button
          aria-pressed={tab === "package"}
          onClick={() => setTab("package")}
        >
          {t("4. Application package")}
        </button>
      </nav>
      <div id="job-stage" tabIndex={-1} />
      {notice && tab === "analyse" && <p role="status">{t(notice)}</p>}
      {tab === "package" && (
        <PackagePanel
          key={`${job.id}:${job.version}:${profile.version}`}
          job={job}
          profile={profile}
          facts={facts}
        />
      )}
      {tab === "review" && (
        <details
          className="disclosure"
          open={!job.title && !job.requirements.length}
        >
          <summary>{t("AI reading assistant")}</summary>
          <AiJobTools job={job} saved={() => setRefresh(refresh + 1)} />
        </details>
      )}
      {tab === "review" && (
        <details className="disclosure">
          <summary>{t("Research and duplicate checks")}</summary>
          <ResearchPanel key={`${job.id}:${job.version}`} job={job} />
          <DuplicateReview
            key={`duplicates-${job.version}`}
            job={job}
            saved={() => setRefresh(refresh + 1)}
          />
        </details>
      )}
      {tab === "review" && (
        <JobReview
          key={job.version}
          job={job}
          saved={(updated) => {
            setJob(updated);
            setMatch(null);
            setNotice(
              "Job review saved. Continue with the requirement assessment.",
            );
            setTab("analyse");
          }}
        />
      )}
      {tab === "analyse" && (
        <AnalysisForm
          key={`${job.version}:${profile.version}`}
          job={job}
          profile={profile}
          facts={facts}
          onReview={() => setTab("review")}
          onResult={(result) => {
            setMatch(result);
            setTab("result");
            setRefresh(refresh + 1);
          }}
        />
      )}
      {tab === "result" &&
        (match ? (
          <MatchResult match={match} />
        ) : (
          <section className="empty">
            <h2>{t("Analysis not yet performed")}</h2>
            <p>
              {t(
                "Review the vacancy and assess its requirements to get a result.",
              )}
            </p>
          </section>
        ))}
    </>
  );
}
function JobReview({
  job,
  saved,
}: {
  job: Job;
  saved: (updated: Job) => void;
}) {
  const [requirements, setRequirements] = useState<Requirement[]>(
    job.requirements,
  );
  const task = useTask();
  const [reviewError, setReviewError] = useState(false);
  const [expandedRequirement, setExpandedRequirement] = useState<string | null>(
    null,
  );
  function change(id: string, update: Partial<Requirement>) {
    setRequirements((items) =>
      items.map((item) => (item.id === id ? { ...item, ...update } : item)),
    );
  }
  return (
    <div className="split review-layout">
      <section className="panel">
        <h2>{t("Check the essentials")}</h2>
        <p className="muted">
          {t(
            "Review the details below. Leave anything the advert does not tell you as unknown.",
          )}
        </p>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            if (!data.has("review_confirmed")) {
              setReviewError(true);
              event.currentTarget
                .querySelector<HTMLInputElement>("[name=review_confirmed]")
                ?.focus();
              return;
            }
            const minimum = optional(data, "salary_min");
            const maximum = optional(data, "salary_max");
            const currency = optional(data, "currency");
            const period = optional(data, "period");
            void task.run(async () => {
              const updated = await api<Job>(`/jobs/${job.id}`, "PATCH", {
                expected_version: job.version,
                title: optional(data, "title"),
                company_name: optional(data, "company_name"),
                location: optional(data, "location"),
                country: optional(data, "country"),
                work_mode: optional(data, "work_mode"),
                employment_type: optional(data, "employment_type"),
                seniority: optional(data, "seniority"),
                salary:
                  minimum || maximum || currency || period
                    ? {
                        minimum: minimum ? Number(minimum) : null,
                        maximum: maximum ? Number(maximum) : null,
                        currency,
                        period,
                      }
                    : null,
                sponsorship: optional(data, "sponsorship"),
                work_authorisation: optional(data, "work_authorisation"),
                requirements,
                risk_flags: String(data.get("risk_flags") ?? "")
                  .split("\n")
                  .map((flag) => flag.trim())
                  .filter(Boolean),
                archived: data.has("archived"),
                review_confirmed: data.has("review_confirmed"),
              });
              saved(updated);
            });
          }}
        >
          <Field label={t("Title")}>
            <input name="title" defaultValue={job.title ?? ""} />
          </Field>
          <Field label={t("Company")}>
            <input name="company_name" defaultValue={job.company_name ?? ""} />
          </Field>
          <div className="form-grid">
            <Field label={t("Location")}>
              <input name="location" defaultValue={job.location ?? ""} />
            </Field>
            <Field label={t("Country")}>
              <select name="country" defaultValue={job.country ?? ""}>
                <option value="">{t("Unknown")}</option>
                <option value="IE">{t("Ireland")}</option>
                <option value="GB">{t("United Kingdom")}</option>
                <option value="OTHER">{t("Other")}</option>
              </select>
            </Field>
            <Field label={t("Working arrangement")}>
              <select name="work_mode" defaultValue={job.work_mode ?? ""}>
                <option value="">{t("Unknown")}</option>
                <option value="hybrid">{t("Hybrid")}</option>
                <option value="onsite">{t("On-site")}</option>
                <option value="remote">{t("Remote")}</option>
              </select>
            </Field>
            <Field label={t("Contract / hours")}>
              <input
                name="employment_type"
                defaultValue={job.employment_type ?? ""}
                placeholder={t("E.g.: full-time")}
              />
            </Field>
          </div>
          <Field label={t("Confirmed vacancy level")}>
            <input
              name="seniority"
              defaultValue={job.seniority ?? ""}
              placeholder="graduate, junior, mid, senior…"
            />
          </Field>
          <details className="disclosure">
            <summary>
              {t("Salary and work eligibility")}
              {(job.sponsorship || job.work_authorisation) && (
                <span className="tag">{t("Review required")}</span>
              )}
            </summary>
            <fieldset>
              <legend>{t("Salary \u2014 leave empty if absent")}</legend>
              <div className="form-grid">
                <Field label={t("Minimum")}>
                  <input
                    type="number"
                    min="0"
                    step="any"
                    name="salary_min"
                    defaultValue={job.salary?.minimum ?? ""}
                  />
                </Field>
                <Field label={t("Maximum")}>
                  <input
                    type="number"
                    min="0"
                    step="any"
                    name="salary_max"
                    defaultValue={job.salary?.maximum ?? ""}
                  />
                </Field>
                <Field label={t("Currency")}>
                  <input
                    name="currency"
                    pattern="[A-Z]{3}"
                    placeholder="EUR"
                    defaultValue={job.salary?.currency ?? ""}
                  />
                </Field>
                <Field label={t("Period")}>
                  <select name="period" defaultValue={job.salary?.period ?? ""}>
                    <option value="">{t("Unknown")}</option>
                    <option value="year">{t("Year")}</option>
                    <option value="month">{t("Month")}</option>
                    <option value="day">{t("Day")}</option>
                    <option value="hour">{t("Hour")}</option>
                  </select>
                </Field>
              </div>
            </fieldset>
            <Field label={t("Declared sponsorship")}>
              <select name="sponsorship" defaultValue={job.sponsorship ?? ""}>
                <option value="">{t("Unknown")}</option>
                <option value="available">{t("Available")}</option>
                <option value="unavailable">
                  {t("Explicitly unavailable")}
                </option>
                <option value="conditional">{t("Conditional")}</option>
              </select>
            </Field>
            <Field label={t("Authorisation / restrictions in advert")}>
              <textarea
                name="work_authorisation"
                defaultValue={job.work_authorisation ?? ""}
                rows={2}
              />
            </Field>
          </details>
          <Field label={t("Review points (one per line)")}>
            <textarea
              name="risk_flags"
              rows={3}
              defaultValue={job.risk_flags.join("\n")}
              placeholder={t(
                "E.g.: title and description show different roles",
              )}
            />
          </Field>
          <h3>{t("Requirements")}</h3>
          <p className="muted">
            {t(
              "Transcribe the relevant criteria and where they appear in the advert. Absence of information remains unknown.",
            )}
          </p>
          {requirements.map((req, index) => (
            <details
              className="disclosure"
              key={req.id}
              open={expandedRequirement === req.id}
            >
              <summary
                onClick={(event) => {
                  event.preventDefault();
                  setExpandedRequirement((current) =>
                    current === req.id ? null : req.id,
                  );
                }}
              >
                {req.text || t("New requirement")}
                {req.is_eliminatory && (
                  <span className="tag blocker">{t("Explicit blocker")}</span>
                )}
                <span className="tag">
                  {req.importance === "required"
                    ? t("Mandatory")
                    : t("Desirable")}
                </span>
              </summary>
              <fieldset>
                <legend>
                  {t("Requirement ")}
                  {index + 1}
                </legend>
                <Field label={t("Requirement description")}>
                  <input
                    required
                    value={req.text}
                    onChange={(event) =>
                      change(req.id, { text: event.target.value })
                    }
                  />
                </Field>
                <Field label={t("Requirement category")}>
                  <select
                    value={req.category}
                    onChange={(event) =>
                      change(req.id, {
                        category: event.target.value as Category,
                      })
                    }
                  >
                    {Object.entries(categories).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label={t("Importance")}>
                  <select
                    value={req.importance}
                    onChange={(event) =>
                      change(req.id, {
                        importance: event.target
                          .value as Requirement["importance"],
                      })
                    }
                  >
                    <option value="required">{t("Mandatory")}</option>
                    <option value="preferred">{t("Desirable")}</option>
                  </select>
                </Field>
                <Field label={t("Location in the advert")}>
                  <input
                    required
                    value={req.source_locator}
                    onChange={(event) =>
                      change(req.id, { source_locator: event.target.value })
                    }
                  />
                </Field>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={req.is_eliminatory}
                    onChange={(event) =>
                      change(req.id, { is_eliminatory: event.target.checked })
                    }
                  />
                  {t("Explicitly confirmed disqualifying requirement")}
                </label>
                {req.category === "work_authorisation_hours" && (
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={req.future_authorisation}
                      onChange={(event) =>
                        change(req.id, {
                          future_authorisation: event.target.checked,
                        })
                      }
                    />
                    {t("Future possibility of authorisation / sponsorship")}
                  </label>
                )}
                <button
                  type="button"
                  onClick={() =>
                    setRequirements((items) =>
                      items.filter((item) => item.id !== req.id),
                    )
                  }
                >
                  {t("Remove requirement ")}
                  {index + 1}
                </button>
              </fieldset>
            </details>
          ))}
          <button
            type="button"
            disabled={requirements.length >= 100}
            onClick={() => {
              const id = crypto.randomUUID();
              setExpandedRequirement(id);
              setRequirements((items) => [
                ...items,
                {
                  id,
                  text: "",
                  category: "technical_skills",
                  importance: "required",
                  is_eliminatory: false,
                  source_locator: "",
                  future_authorisation: false,
                },
              ]);
            }}
          >
            {t("Add requirement")}
          </button>
          <label className="check">
            <input
              name="archived"
              type="checkbox"
              defaultChecked={job.archived}
              aria-describedby="archive-help"
            />
            {t("Archive this opportunity")}
          </label>
          <details className="help-disclosure" id="archive-help">
            <summary>
              <span aria-hidden="true">ⓘ</span>
              {t(" What does archiving do?")}
            </summary>
            <p>
              {t(
                "Archiving hides this opportunity from the active Inbox. It keeps the job, evidence and application history. Find it with the archived filter and clear this checkbox to restore it.",
              )}
            </p>
          </details>
          <label className="check">
            <input
              name="review_confirmed"
              type="checkbox"
              required
              aria-invalid={reviewError}
              aria-describedby="job-review-help"
              onInvalid={() => setReviewError(true)}
              onChange={() => setReviewError(false)}
            />
            {t("I confirm the review of the fields and requirements above.")}
          </label>
          <p id="job-review-help" role={reviewError ? "alert" : undefined}>
            {reviewError
              ? t("Confirm the review checkbox before saving the job review.")
              : t(
                  "Review confirmation is required to save. Check the fields and requirements, then tick the confirmation box.",
                )}
          </p>
          {task.feedback}
          <button className="primary" disabled={task.busy}>
            {t("Save vacancy review")}
          </button>
        </form>
      </section>
      <aside className="panel source">
        <details>
          <summary>{t("Original advert")}</summary>
          <p>
            {t("Source: ")}
            {job.source_name}
          </p>
          {job.source_url && (
            <a href={job.source_url} target="_blank" rel="noopener noreferrer">
              {t("Open external reference \u2197")}
            </a>
          )}
          <p className="preserve">{job.raw_text}</p>
          <details>
            <summary>{t("Text integrity")}</summary>
            <p className="muted">SHA-256: {job.content_sha256}</p>
          </details>
        </details>
      </aside>
    </div>
  );
}
function AnalysisForm({
  job,
  profile,
  facts,
  onResult,
  onReview,
}: {
  job: Job;
  profile: Profile;
  facts: Fact[];
  onResult: (result: Match) => void;
  onReview: () => void;
}) {
  const task = useTask();
  const [aiRun, setAiRun] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const [resolutions, setResolutions] = useState<Resolution[]>([]);
  const [confirmed, setConfirmed] = useState(false);
  const [assessments, setAssessments] = useState<Assessment[]>(() =>
    job.requirements.map((req) => ({
      requirement_id: req.id,
      status: "unknown",
      reason: "",
      fact_ids: [],
    })),
  );
  function change(id: string, update: Partial<Assessment>) {
    setConfirmed(false);
    setAssessments((items) =>
      items.map((item) =>
        item.requirement_id === id ? { ...item, ...update } : item,
      ),
    );
  }
  if (job.status === "DISCOVERED" || profile.status !== "reviewed")
    return (
      <section className="empty">
        <h2>{t("Review required")}</h2>
        <p>
          {t(
            "Confirm the job review and publish the profile version before analysing.",
          )}
        </p>
        <a href="#profile">{t("Review profile \u2192")}</a>
      </section>
    );
  if (!job.requirements.length)
    return (
      <section className="empty">
        <h2>{t("Add requirements before assessing this job")}</h2>
        <p>
          {t(
            "Return to the job review to extract or add its requirements, then save and continue.",
          )}
        </p>
        <button onClick={onReview}>{t("Back to job review")}</button>
      </section>
    );
  return (
    <section className="panel narrow">
      <h2>{t("Assess each requirement")}</h2>
      <AiMatching
        job={job}
        profile={profile}
        facts={facts}
        changed={() => {
          setRevision((value) => value + 1);
          setResolutions([]);
          setConfirmed(false);
        }}
        apply={(items, run) => {
          setAssessments(items);
          setAiRun(run);
          setConfirmed(false);
        }}
      />
      <Clarifications
        job={job}
        profile={profile}
        assessments={assessments}
        revision={revision}
        resolutions={resolutions}
        change={(value) => {
          setResolutions(value);
          setConfirmed(false);
        }}
      />
      <p>
        {t(
          "Only verified and authorised facts for matching can support positive responses. A manual review does not create professional experience.",
        )}
      </p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void task.run(async () => {
            onResult(
              await api<Match>(`/jobs/${job.id}/analyse`, "POST", {
                job_version: job.version,
                profile_version: profile.version,
                review_confirmed: true,
                ai_run_id: aiRun,
                clarification_resolutions: resolutions.filter(
                  (r) =>
                    r.note.trim().length >= 20 &&
                    r.source_reference.trim().length >= 5,
                ),
                assessments: assessments.map((a) => ({
                  ...a,
                  reason: a.reason || t("Information still unknown."),
                })),
              }),
            );
          }, t("Analysis completed."));
        }}
      >
        {!job.requirements.length && (
          <p>
            {t(
              "No structured requirements: the result will have unknown score and zero coverage.",
            )}
          </p>
        )}
        {job.requirements.map((req) => {
          const entry = assessments.find((a) => a.requirement_id === req.id)!;
          return (
            <fieldset key={req.id}>
              <legend>{req.text}</legend>
              <p className="muted">
                {categories[req.category]} ·{" "}
                {req.importance === "required"
                  ? t("Mandatory")
                  : t("Desirable")}
                {req.is_eliminatory ? t(" \u00B7 Disqualifying") : ""}
              </p>
              <Field label={t("Attainment: {0}", [req.text])}>
                <select
                  value={entry.status}
                  onChange={(event) =>
                    change(req.id, { status: event.target.value })
                  }
                >
                  {Object.entries(outcomes).map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label={t("Justification: {0}", [req.text])}>
                <textarea
                  rows={2}
                  required={entry.status !== "unknown"}
                  maxLength={3000}
                  value={entry.reason}
                  onChange={(event) =>
                    change(req.id, { reason: event.target.value })
                  }
                />
              </Field>
              <fieldset>
                <legend>{t("Facts supporting this assessment")}</legend>
                {facts
                  .filter(
                    (fact) =>
                      fact.status === "verified" &&
                      fact.allowed_uses.includes("matching"),
                  )
                  .map((fact) => (
                    <label className="check" key={fact.id}>
                      <input
                        type="checkbox"
                        checked={entry.fact_ids.includes(fact.id)}
                        onChange={(event) =>
                          change(req.id, {
                            fact_ids: event.target.checked
                              ? [...entry.fact_ids, fact.id]
                              : entry.fact_ids.filter((id) => id !== fact.id),
                          })
                        }
                      />
                      {fact.claim}
                    </label>
                  ))}
                {!facts.some(
                  (f) =>
                    f.status === "verified" &&
                    f.allowed_uses.includes("matching"),
                ) && <p>{t("No verified facts available.")}</p>}
              </fieldset>
            </fieldset>
          );
        })}
        <label className="check">
          <input
            type="checkbox"
            required
            checked={confirmed}
            onChange={(event) => setConfirmed(event.target.checked)}
          />
          {t(
            "I confirm these assessments and the validity of the selected references.",
          )}
        </label>
        {task.feedback}
        <button className="primary" disabled={task.busy}>
          {t("Calculate compatibility")}
        </button>
      </form>
    </section>
  );
}
export function MatchResult({ match }: { match: Match }) {
  return (
    <section className="match-result">
      {match.stale && (
        <p role="alert">
          {t(
            "Outdated analysis: the profile, job or fact validity has changed. Review and recalculate.",
          )}
        </p>
      )}
      <div className="score-grid">
        <div>
          <span>{t("Compatibility")}</span>
          <strong>{match.score === null ? "—" : `${match.score}%`}</strong>
          <small>
            {match.score === null
              ? t("Insufficient data")
              : t("Attainment against known criteria")}
          </small>
        </div>
        <div>
          <span>{t("Coverage")}</span>
          <strong>{Math.round(match.coverage * 100)}%</strong>
          <small>{t("Proportion of requirements assessed")}</small>
        </div>
        <div>
          <span>{t("Recommendation")}</span>
          <h2>{recommendations[match.recommendation]}</h2>
          <small>{gates[match.employment_gate]}</small>
        </div>
      </div>
      <section className="panel">
        <h2>{t("Blockers and gaps")}</h2>
        <ClarificationList issues={match.clarifications ?? []} />
        {match.clarification_resolutions?.map((item) => (
          <p key={item.key}>
            {t("Clarification recorded: ")}
            {item.note}
            {t(" \u00B7 Source:")} {item.source_reference}
          </p>
        ))}
        {match.blockers.map((b, i) => (
          <p className="blocker" key={i}>
            {systemMessage(b.reason)}
          </p>
        ))}
        {!match.gaps.length && !match.blockers.length && (
          <p>{t("No gap between the assessed criteria.")}</p>
        )}
        {match.gaps.map((gap) => (
          <article className="record" key={gap.requirement_id}>
            <h3>
              {gap.text} · {outcomes[gap.status]}
            </h3>
            <p>{systemMessage(gap.reason)}</p>
          </article>
        ))}
        {match.review_flags.length > 0 && (
          <p className="muted">
            {t("Review points:")}{" "}
            {match.review_flags
              .map((flag) => reviewFlags[flag] ?? flag)
              .join(", ")}
          </p>
        )}
      </section>
      <section className="panel">
        <h2>{t("How the result was calculated")}</h2>
        {match.breakdown.map((category) => (
          <details className="category" key={category.category}>
            <summary>
              {categories[category.category]}
              {t(" \u00B7 weight ")}
              {category.weight}
              {t(" \u00B7 coverage ")}
              {Math.round(category.coverage * 100)}%
            </summary>
            {!category.assessments.length && (
              <p>{t("No structured criteria in this category.")}</p>
            )}
            {category.assessments.map((item) => (
              <article key={item.requirement_id} className="record">
                <p>
                  <strong>{outcomes[item.status]}</strong> ·{" "}
                  {systemMessage(item.reason)}
                </p>
                {item.fact_ids.map((id) => (
                  <p key={id}>
                    {t("Fact:")}{" "}
                    {match.profile_snapshot.facts.find((fact) => fact.id === id)
                      ?.claim || id}
                  </p>
                ))}
                {item.evidence_ids.map((id) => {
                  const evidence = match.profile_snapshot.evidence.find(
                    (e) => e.id === id,
                  );
                  return evidence ? (
                    <details key={id}>
                      <summary>
                        {t("View evidence: ")}
                        {evidence.source_ref}
                      </summary>
                      <p>{evidence.locator}</p>
                      <p className="preserve">{evidence.content}</p>
                      <p className="muted">
                        {t("Version ")}
                        {evidence.version}
                        {t(" preserved in this analysis.")}
                      </p>
                    </details>
                  ) : null;
                })}
              </article>
            ))}
          </details>
        ))}
      </section>
      <ShortlistButton match={match} />
    </section>
  );
}

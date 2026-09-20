import { useEffect, useState } from "react";
import { api } from "./api";
import { t } from "./i18n";
import type { Job, Profile } from "./types";
import { ErrorState, Field, Loading } from "./ui";
import Icon from "./Icon";

const initialFilters = {
  q: "",
  location: "",
  work_mode: "",
  status: "",
  archived: false,
};

export default function Opportunities({ profile }: { profile?: Profile }) {
  const [filters, setFilters] = useState(initialFilters);
  const [draft, setDraft] = useState(initialFilters);
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [result, setResult] = useState<{ items: Job[]; total: number } | null>(
    null,
  );
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    const query = new URLSearchParams({
      limit: "20",
      offset: String(offset),
      q: filters.q,
      archived: String(filters.archived),
    });
    if (filters.status) query.set("status", filters.status);
    if (filters.location) query.set("location", filters.location);
    if (filters.work_mode) query.set("work_mode", filters.work_mode);
    api<{ items: Job[]; total: number }>(`/jobs?${query}`)
      .then((data) => {
        if (active) {
          setResult(data);
          setError("");
        }
      })
      .catch((reason: Error) => {
        if (active) setError(reason.message);
      });
    return () => {
      active = false;
    };
  }, [filters, offset, refresh]);
  function search(next: typeof filters) {
    setError("");
    setResult(null);
    setOffset(0);
    setFilters({ ...next });
  }
  const filtered = Object.values(filters).some(Boolean);
  const ready = profile?.status === "reviewed";
  return (
    <>
      <header className="page-heading">
        <div>
          <p className="eyebrow">{t("MAKE ROOM FOR WHAT IS NEXT")}</p>
          <h1>{t("Your opportunities")}</h1>
          <p>{t("Find a role that fits the life you want to build.")}</p>
        </div>
        <a className="button primary" href="#discover">
          <Icon name="sparkle" />
          {t("Discover opportunities")}
        </a>
      </header>
      {profile && !ready && (
        <section className="welcome-card" aria-labelledby="welcome-heading">
          <div className="welcome-copy">
            <span className="tag">{t("LET US START WITH YOU")}</span>
            <h2 id="welcome-heading">
              {profile.display_name
                ? t("Your experience deserves a good match.")
                : t("One CV. A clearer starting point.")}
            </h2>
            <p>
              {t(
                "Upload your CV and let AI organise your experience. You review the details, then explore opportunities with your profile in mind.",
              )}
            </p>
            <a className="button primary" href="#profile">
              {profile.display_name
                ? t("Finish my profile")
                : t("Set up my profile")}
              <Icon name="arrow" />
            </a>
          </div>
          <ol className="journey-list">
            <li>
              <span>01</span>
              <div>
                <strong>{t("Bring your experience")}</strong>
                <small>{t("Upload a CV or add your details.")}</small>
              </div>
            </li>
            <li>
              <span>02</span>
              <div>
                <strong>{t("Make it yours")}</strong>
                <small>{t("Review what AI finds. You stay in control.")}</small>
              </div>
            </li>
            <li>
              <span>03</span>
              <div>
                <strong>{t("Find your fit")}</strong>
                <small>{t("Add vacancies and see how they compare.")}</small>
              </div>
            </li>
          </ol>
        </section>
      )}
      {ready && (
        <div className="profile-ready">
          <Icon name="check" />
          <span>
            {t("Your profile is ready. Add a vacancy to explore your fit.")}
          </span>
          <a href="#profile">{t("Update profile")}</a>
        </div>
      )}
      <section
        className="opportunities-section"
        aria-labelledby="saved-jobs-heading"
      >
        <div className="section-heading">
          <div>
            <h2 id="saved-jobs-heading">{t("Saved opportunities")}</h2>
            <p className="muted">
              {t(
                "Vacancies you add appear here. Use the filters to narrow your list.",
              )}
            </p>
          </div>
        </div>
        <form
          className="search-panel"
          onSubmit={(event) => {
            event.preventDefault();
            search(draft);
          }}
        >
          <div className="search-fields">
            <Field label={t("Search title or company")}>
              <input
                type="search"
                name="q"
                maxLength={200}
                value={draft.q}
                onChange={(e) => setDraft({ ...draft, q: e.target.value })}
                placeholder={t("E.g.: Junior Python")}
              />
            </Field>
            <Field label={t("Location filter")}>
              <input
                name="location"
                maxLength={200}
                value={draft.location}
                onChange={(e) =>
                  setDraft({ ...draft, location: e.target.value })
                }
                placeholder={t("Any location")}
              />
            </Field>
            <Field label={t("Working arrangement filter")}>
              <select
                name="work_mode"
                value={draft.work_mode}
                onChange={(e) =>
                  setDraft({ ...draft, work_mode: e.target.value })
                }
              >
                <option value="">{t("Any arrangement")}</option>
                <option value="remote">{t("Remote")}</option>
                <option value="hybrid">{t("Hybrid")}</option>
                <option value="onsite">{t("On-site")}</option>
              </select>
            </Field>
            <button className="primary">
              <Icon name="search" />
              {t("Filter")}
            </button>
          </div>
          <details className="filter-details">
            <summary>
              {t("More filters")}
              {(filters.status || filters.archived) && (
                <span className="tag">{t("Active")}</span>
              )}
            </summary>
            <div className="filters">
              <Field label={t("Stage")}>
                <select
                  name="status"
                  value={draft.status}
                  onChange={(e) =>
                    setDraft({ ...draft, status: e.target.value })
                  }
                >
                  <option value="">{t("All")}</option>
                  <option value="DISCOVERED">{t("Imported")}</option>
                  <option value="PARSED">{t("Reviewed")}</option>
                  <option value="SCORED">{t("Analysed")}</option>
                </select>
              </Field>
              <label className="check">
                <input
                  type="checkbox"
                  name="archived"
                  checked={draft.archived}
                  onChange={(e) =>
                    setDraft({ ...draft, archived: e.target.checked })
                  }
                />
                {t("Archived")}
              </label>
              <p className="muted">
                {t(
                  "Location and arrangement filters exclude vacancies where these details are unknown.",
                )}
              </p>
            </div>
          </details>
        </form>
        {filtered && (
          <div className="filter-summary">
            <p>{t("Filters are applied to your saved opportunities.")}</p>
            <button
              onClick={() => {
                setDraft(initialFilters);
                search(initialFilters);
              }}
            >
              {t("Clear filters")}
            </button>
          </div>
        )}
        {error ? (
          <ErrorState
            error={error}
            retry={() => {
              setError("");
              setRefresh(refresh + 1);
            }}
          />
        ) : !result ? (
          <Loading />
        ) : (
          <>
            <p className="results-count" aria-live="polite">
              {t("{0} opportunities", [result.total])}
            </p>
            {!result.items.length ? (
              <section className="empty">
                <span className="empty-icon">
                  <Icon name={filtered ? "search" : "briefcase"} />
                </span>
                <h2>{t("No vacancies in this selection")}</h2>
                <p>
                  {filtered
                    ? t(
                        "Try another location or clear your filters to see more opportunities.",
                      )
                    : t(
                        "Found something interesting? Paste a vacancy link and we will help you understand it.",
                      )}
                </p>
                {filtered ? (
                  <button
                    onClick={() => {
                      setDraft(initialFilters);
                      search(initialFilters);
                    }}
                  >
                    {t("Show all opportunities")}
                  </button>
                ) : (
                  <a className="button primary" href="#import">
                    {t("Add your first opportunity")}
                    <Icon name="arrow" />
                  </a>
                )}
              </section>
            ) : (
              <ul className="job-list">
                {result.items.map((job) => (
                  <li key={job.id}>
                    <a href={`#job/${job.id}`}>
                      <span className="company-mark" aria-hidden="true">
                        {(job.company_name || job.title || "J")
                          .slice(0, 1)
                          .toUpperCase()}
                      </span>
                      <div className="job-copy">
                        <p className="company-name">
                          {job.company_name || t("Company not provided")}
                        </p>
                        <h2>{job.title || t("Job awaiting review")}</h2>
                        <p className="job-meta">
                          <Icon name="pin" />
                          {job.location || t("Location not provided")}
                          {job.work_mode && (
                            <>
                              {" "}
                              ·{" "}
                              {
                                (
                                  {
                                    remote: t("Remote"),
                                    hybrid: t("Hybrid"),
                                    onsite: t("On-site"),
                                  } as Record<string, string>
                                )[job.work_mode]
                              }
                            </>
                          )}
                        </p>
                      </div>
                      <span className={`tag stage-${job.status.toLowerCase()}`}>
                        {
                          (
                            {
                              DISCOVERED: t("Imported"),
                              PARSED: t("Reviewed"),
                              SCORED: t("Analysed"),
                            } as Record<string, string>
                          )[job.status]
                        }
                      </span>
                      <Icon name="arrow" />
                    </a>
                  </li>
                ))}
              </ul>
            )}
            {result.total > 20 && (
              <div className="pagination">
                <button
                  disabled={offset === 0}
                  onClick={() => {
                    setResult(null);
                    setOffset(Math.max(0, offset - 20));
                  }}
                >
                  {t("Previous")}
                </button>
                <span>{t("Page {0}", [Math.floor(offset / 20) + 1])}</span>
                <button
                  disabled={offset + 20 >= result.total}
                  onClick={() => {
                    setResult(null);
                    setOffset(offset + 20);
                  }}
                >
                  {t("Next")}
                </button>
              </div>
            )}
          </>
        )}
      </section>
    </>
  );
}

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import { t } from "./i18n";
import { ErrorState, Field, Loading } from "./ui";
import { useTask } from "./useTask";
import type { Job, Profile } from "./types";
import type { DiscoveryItem, DiscoverySource } from "./discoveryTypes";
import DiscoverySources from "./DiscoverySources";
import { discoveryDate, preferenceHints } from "./discoveryUtils";
import { takeOAuthReturn } from "./oauthReturn";

export default function Discovery({ profile }: { profile: Profile }) {
  const [sources, setSources] = useState<DiscoverySource[]>([]);
  const [configured, setConfigured] = useState(false);
  const [page, setPage] = useState<{
    items: DiscoveryItem[];
    total: number;
  } | null>(null);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState({
    q: "",
    source: "",
    unread: false,
    dismissed: false,
  });
  const [draft, setDraft] = useState("");
  const [offset, setOffset] = useState(0);
  const [reload, setReload] = useState(0);
  const [manage, setManage] = useState(false);
  const oauthStarted = useRef(false);
  const task = useTask();
  const { run } = task;
  const refresh = useCallback(async () => {
    const [newSources, gmail] = await Promise.all([
      api<DiscoverySource[]>("/discovery/sources"),
      api<{ configured: boolean }>("/discovery/gmail/status"),
    ]);
    setSources(newSources);
    setConfigured(gmail.configured);
    setReload((value) => value + 1);
  }, []);
  useEffect(() => {
    if (oauthStarted.current) return;
    oauthStarted.current = true;
    const result = takeOAuthReturn();
    if (result) {
      void run(async () => {
        if (result.error)
          throw new Error(
            t(
              "Gmail connection was cancelled. You can start again when ready.",
            ),
          );
        await api("/discovery/gmail/complete", "POST", {
          code: result.code,
          state: result.state,
        });
        setManage(true);
        await refresh();
      }, t("Gmail connected. Choose a label before enabling checks."));
    }
  }, [run, refresh]);
  useEffect(() => {
    let active = true;
    const query = new URLSearchParams({
      q: filters.q,
      limit: "20",
      offset: String(offset),
      unread: String(filters.unread),
      dismissed: String(filters.dismissed),
    });
    if (filters.source) query.set("source_id", filters.source);
    Promise.all([
      api<{ items: DiscoveryItem[]; total: number }>(
        `/discovery/items?${query}`,
      ),
      api<DiscoverySource[]>("/discovery/sources"),
      api<{ configured: boolean }>("/discovery/gmail/status"),
    ])
      .then(([items, newSources, gmail]) => {
        if (active) {
          setPage(items);
          setSources(newSources);
          setConfigured(gmail.configured);
          setError("");
        }
      })
      .catch((reason: Error) => {
        if (active) setError(reason.message);
      });
    return () => {
      active = false;
    };
  }, [filters, offset, reload]);
  function changeFilters(value: typeof filters) {
    setPage(null);
    setOffset(0);
    setFilters(value);
  }
  return (
    <>
      <header className="page-heading">
        <div>
          <p className="eyebrow">{t("A LITTLE LESS SEARCHING")}</p>
          <h1>{t("Discover opportunities")}</h1>
          <p>
            {t(
              "Fresh leads from sources you choose. Review what matters, then save a vacancy to assess your fit.",
            )}
          </p>
        </div>
        <a className="button" href="#inbox">
          {t("Saved opportunities")}
        </a>
      </header>
      {task.feedback}
      {error ? (
        <ErrorState
          error={error}
          retry={() => setReload((value) => value + 1)}
        />
      ) : !page ? (
        <Loading />
      ) : (
        <>
          <details
            className="panel discovery-settings"
            open={manage || sources.length === 0}
            onToggle={(e) => setManage(e.currentTarget.open)}
          >
            <summary>{t("Manage sources")}</summary>
            <DiscoverySources
              sources={sources}
              refresh={refresh}
              gmailConfigured={configured}
            />
          </details>
          {sources.some((source) => source.enabled && !source.ready) && (
            <p role="status">
              {t(
                "A source needs a new access review. Open Manage sources to resume checking.",
              )}
            </p>
          )}
          <form
            className="search-panel"
            onSubmit={(event) => {
              event.preventDefault();
              changeFilters({ ...filters, q: draft });
            }}
          >
            <div className="search-fields">
              <Field label={t("Search discovered opportunities")}>
                <input
                  type="search"
                  maxLength={200}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                />
              </Field>
              <Field label={t("Source filter")}>
                <select
                  value={filters.source}
                  onChange={(e) =>
                    changeFilters({ ...filters, source: e.target.value })
                  }
                >
                  <option value="">{t("All sources")}</option>
                  {sources.map((source) => (
                    <option key={source.id} value={source.id}>
                      {source.name}
                    </option>
                  ))}
                </select>
              </Field>
              <button>{t("Search")}</button>
            </div>
            <div className="actions">
              <label className="check">
                <input
                  type="checkbox"
                  checked={filters.unread}
                  onChange={(e) =>
                    changeFilters({ ...filters, unread: e.target.checked })
                  }
                />
                {t("Only unseen updates")}
              </label>
              <label className="check">
                <input
                  type="checkbox"
                  checked={filters.dismissed}
                  onChange={(e) =>
                    changeFilters({ ...filters, dismissed: e.target.checked })
                  }
                />
                {t("Show dismissed items")}
              </label>
              {(filters.q ||
                filters.source ||
                filters.unread ||
                filters.dismissed) && (
                <button
                  type="button"
                  onClick={() => {
                    setDraft("");
                    changeFilters({
                      q: "",
                      source: "",
                      unread: false,
                      dismissed: false,
                    });
                  }}
                >
                  {t("Clear filters")}
                </button>
              )}
            </div>
          </form>
          <div className="section-heading">
            <h2>{t("Latest discoveries")}</h2>
            <span className="quiet-label">{t("{0} items", [page.total])}</span>
          </div>
          {page.total === 0 ? (
            <section className="empty-state panel">
              <h3>{t("A quieter search starts here.")}</h3>
              <p>
                {sources.length
                  ? t(
                      "No items match this view yet. Check your enabled sources or clear the filters.",
                    )
                  : t(
                      "Add a company board or connect job alerts to start receiving opportunities.",
                    )}
              </p>
            </section>
          ) : (
            <div className="discovery-grid">
              {page.items.map((item) => (
                <DiscoveryCard
                  key={item.id}
                  item={item}
                  profile={profile}
                  source={
                    sources.find((source) => source.id === item.source_id)
                      ?.name ?? t("Source")
                  }
                  refresh={refresh}
                />
              ))}
            </div>
          )}
          {page.total > 20 && (
            <nav className="pagination" aria-label={t("Discovery pages")}>
              <button
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - 20))}
              >
                {t("Previous")}
              </button>
              <span>{t("Page {0}", [offset / 20 + 1])}</span>
              <button
                disabled={offset + 20 >= page.total}
                onClick={() => setOffset(offset + 20)}
              >
                {t("Next")}
              </button>
            </nav>
          )}
        </>
      )}
    </>
  );
}

function DiscoveryCard({
  item,
  profile,
  source,
  refresh,
}: {
  item: DiscoveryItem;
  profile: Profile;
  source: string;
  refresh: () => Promise<void>;
}) {
  const task = useTask();
  const hints = preferenceHints(item, profile);
  const [savedJob, setSavedJob] = useState<Job | null>(null);
  const [replace, setReplace] = useState(false);
  return (
    <article className="panel discovery-card">
      <div className="actions">
        <span className="tag">
          {item.item_type === "email" ? t("Email alert") : t("Vacancy")}
        </span>
        {!item.seen && (
          <span className="tag accent">
            {item.notice === "new"
              ? t("New")
              : item.notice === "changed"
                ? t("Source updated")
                : t("No longer listed")}
          </span>
        )}
      </div>
      <h3>{item.title}</h3>
      <p>
        {[item.company, item.location].filter(Boolean).join(" · ") ||
          t("Details not provided")}
      </p>
      <p className="muted">
        {source} · {t("Last seen: {0}", [discoveryDate(item.last_seen_at)])}
      </p>
      {hints.length > 0 && (
        <p className="preference-hint">
          {t("Mentions your preferences: {0}", [hints.join(", ")])}
          <small>
            {t(
              "A text hint, not a suitability score. Requirements still need assessment.",
            )}
          </small>
        </p>
      )}
      {item.update_pending && item.job_id && (
        <p className="source-warning">
          {t(
            "The source changed. Your saved review has been preserved; compare the new text before using it.",
          )}
        </p>
      )}
      {item.availability === "not_listed" && (
        <p className="source-warning">
          {t(
            "This post was absent from the latest complete board. Confirm its status with the employer; this is not proof that it has closed.",
          )}
        </p>
      )}
      <details className="disclosure">
        <summary>{t("Read source text")}</summary>
        <pre className="raw-text">{item.raw_text}</pre>
        {item.item_type === "email" && (
          <>
            <p>
              {t(
                "This email may contain several vacancies. Select one public advert link to import; links are not opened automatically.",
              )}
            </p>
            {item.links.map((link, index) => (
              <div className="email-link" key={link}>
                <span>{link}</span>
                <a
                  className="button"
                  href={`#import?url=${encodeURIComponent(link)}`}
                >
                  {t("Review link {0}", [index + 1])}
                </a>
              </div>
            ))}
          </>
        )}
      </details>
      <div className="actions">
        {item.job_id ? (
          <a className="button primary" href={`#job/${item.job_id}`}>
            {t("Open saved vacancy")}
          </a>
        ) : (
          item.item_type === "vacancy" && (
            <button
              className="primary"
              disabled={task.busy || item.availability !== "listed"}
              onClick={() =>
                void task.run(async () => {
                  const job = await api<Job>(
                    `/discovery/items/${item.id}/save`,
                    "POST",
                    { expected_version: item.version },
                  );
                  window.location.hash = `job/${job.id}`;
                }, "")
              }
            >
              {t("Save and review vacancy")}
            </button>
          )
        )}
        <a href={item.url} target="_blank" rel="noopener noreferrer">
          {t("Open original source")}
        </a>
        {!item.seen && (
          <button
            disabled={task.busy}
            onClick={() =>
              void task.run(async () => {
                await api(`/discovery/items/${item.id}`, "PATCH", {
                  expected_version: item.version,
                  seen: true,
                  dismissed: item.dismissed,
                });
                await refresh();
              }, t("Update marked as seen."))
            }
          >
            {t("Mark as seen")}
          </button>
        )}
        <button
          disabled={task.busy}
          onClick={() =>
            void task.run(
              async () => {
                await api(`/discovery/items/${item.id}`, "PATCH", {
                  expected_version: item.version,
                  seen: true,
                  dismissed: !item.dismissed,
                });
                await refresh();
              },
              item.dismissed
                ? t("Item restored.")
                : t("Item dismissed. You can restore it from dismissed items."),
            )
          }
        >
          {item.dismissed ? t("Restore item") : t("Dismiss")}
        </button>
      </div>
      {item.job_id && item.update_pending && item.availability === "listed" && (
        <details className="disclosure">
          <summary>{t("Compare with the saved review")}</summary>
          <button
            disabled={task.busy}
            onClick={() =>
              void task.run(async () => {
                setSavedJob(await api<Job>(`/jobs/${item.job_id}`));
                setReplace(false);
              }, "")
            }
          >
            {t("Load saved advert")}
          </button>
          {savedJob && (
            <>
              <h4>{t("Previously saved text")}</h4>
              <pre className="raw-text">{savedJob.raw_text}</pre>
              <p>
                {t(
                  "Applying the new source text resets extracted fields and makes previous assessments and packages out of date. Review and assess the vacancy again.",
                )}
              </p>
              <label className="check">
                <input
                  type="checkbox"
                  checked={replace}
                  onChange={(e) => setReplace(e.target.checked)}
                />
                {t(
                  "I have compared the texts and want to replace the saved advert for a new review.",
                )}
              </label>
              <button
                disabled={task.busy || !replace}
                onClick={() =>
                  void task.run(async () => {
                    const job = await api<Job>(
                      `/discovery/items/${item.id}/apply-update`,
                      "POST",
                      {
                        expected_version: item.version,
                        expected_job_version: savedJob.version,
                        replacement_confirmed: true,
                      },
                    );
                    window.location.hash = `job/${job.id}`;
                  }, "")
                }
              >
                {t("Apply update and review again")}
              </button>
            </>
          )}
        </details>
      )}
      {task.feedback}
    </article>
  );
}

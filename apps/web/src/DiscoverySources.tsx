import { useEffect, useState } from "react";
import { api } from "./api";
import { t } from "./i18n";
import { sourceError, discoveryDate } from "./discoveryUtils";
import { Field } from "./ui";
import { useTask } from "./useTask";
import type { DiscoveryRun, DiscoverySource } from "./discoveryTypes";

export default function DiscoverySources({
  sources,
  refresh,
  gmailConfigured,
}: {
  sources: DiscoverySource[];
  refresh: () => Promise<void>;
  gmailConfigured: boolean;
}) {
  const task = useTask();
  const [provider, setProvider] = useState("greenhouse");
  const [name, setName] = useState("");
  const [reference, setReference] = useState("");
  return (
    <div className="source-list">
      <p>
        {t(
          "Choose a small number of sources. Only enabled sources are checked, once a day while the local app is running.",
        )}
      </p>
      {sources.map((source) => (
        <SourceCard
          key={source.id}
          source={source}
          refresh={refresh}
          gmailConfigured={gmailConfigured}
        />
      ))}
      <details className="panel" open={sources.length === 0 || undefined}>
        <summary>{t("Add a source")}</summary>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void task.run(async () => {
              await api("/discovery/sources", "POST", {
                provider,
                name,
                reference: provider === "gmail" ? "alerts" : reference,
              });
              setName("");
              setReference("");
              await refresh();
            }, t("Source added. Review its settings before enabling it."));
          }}
        >
          <div className="form-grid">
            <Field label={t("Source type")}>
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
              >
                <option value="greenhouse">Greenhouse</option>
                <option value="gmail">Gmail</option>
              </select>
            </Field>
            <Field label={t("Source name")}>
              <input
                required
                maxLength={100}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t("E.g.: Example company careers")}
              />
            </Field>
            {provider === "greenhouse" && (
              <Field label={t("Greenhouse board token")}>
                <input
                  required
                  pattern="[a-z0-9_-]+"
                  maxLength={100}
                  value={reference}
                  onChange={(e) => setReference(e.target.value)}
                  placeholder="examplecompany"
                />
              </Field>
            )}
          </div>
          <p className="muted">
            {provider === "greenhouse"
              ? t(
                  "Use the company token from its Greenhouse careers URL. A public board still needs an applicable access review.",
                )
              : t(
                  "Create a dedicated Gmail label for job alerts. You will choose it after connecting.",
                )}
          </p>
          {task.feedback}
          <button disabled={task.busy}>{t("Add source")}</button>
        </form>
      </details>
    </div>
  );
}

function SourceCard({
  source,
  refresh,
  gmailConfigured,
}: {
  source: DiscoverySource;
  refresh: () => Promise<void>;
  gmailConfigured: boolean;
}) {
  const task = useTask();
  const [terms, setTerms] = useState(source.terms_url);
  const [note, setNote] = useState(source.permission_note);
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 30000);
    return () => window.clearInterval(timer);
  }, []);
  const [until, setUntil] = useState(
    () =>
      source.review_until ??
      new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10),
  );
  const [confirmed, setConfirmed] = useState(false);
  const [mailConsent, setMailConsent] = useState(false);
  const [labels, setLabels] = useState<{ id: string; name: string }[]>([]);
  const [label, setLabel] = useState(source.label_id);
  const [history, setHistory] = useState<DiscoveryRun[] | null>(null);
  const [disconnecting, setDisconnecting] = useState(false);
  const available = source.provider === "greenhouse" || source.connected;
  const due = !source.next_sync_at || Date.parse(source.next_sync_at) <= now;
  return (
    <article className="panel source-card">
      <div className="section-heading">
        <div>
          <h3>{source.name}</h3>
          <p className="muted">
            {source.provider === "gmail" ? "Gmail" : "Greenhouse"} ·{" "}
            {source.provider === "gmail"
              ? source.label_name || t("No label selected")
              : source.reference}
          </p>
        </div>
        <span className="tag">
          {source.ready
            ? t("Daily checks enabled")
            : source.enabled
              ? t("Access review expired")
              : t("Paused")}
        </span>
      </div>
      <p className="muted">
        {t("Last checked: {0}", [discoveryDate(source.last_synced_at)])}
      </p>
      {source.next_sync_at && (
        <p className="muted">
          {t("Next check: {0}", [discoveryDate(source.next_sync_at)])}
        </p>
      )}
      {source.last_error && (
        <p className="source-warning">{sourceError(source.last_error)}</p>
      )}
      <div className="actions">
        <button
          disabled={
            task.busy || !source.ready || !due || Boolean(source.active_run)
          }
          onClick={() =>
            void task.run(async () => {
              const run = await api<DiscoveryRun>(
                `/discovery/sources/${source.id}/sync`,
                "POST",
              );
              await refresh();
              if (run.status === "failed")
                throw new Error(sourceError(run.error_code));
              if (run.status === "cancelled")
                throw new Error(
                  t(
                    "The source changed during the check. No results were applied.",
                  ),
                );
            }, t("Source checked. New and changed items are ready for review."))
          }
        >
          {task.busy ? t("Checking source…") : t("Check now")}
        </button>
        {source.enabled && (
          <button
            disabled={task.busy}
            onClick={() =>
              void task.run(async () => {
                await api(`/discovery/sources/${source.id}`, "PATCH", {
                  expected_version: source.version,
                  enabled: false,
                });
                await refresh();
              }, t("Source paused."))
            }
          >
            {t("Pause source")}
          </button>
        )}
      </div>
      {source.provider === "gmail" && !source.connected && (
        <div className="gmail-connection">
          {!gmailConfigured ? (
            <p>
              {t(
                "Gmail setup is needed on this computer. Follow docs/phase-4/gmail-setup.md, then restart the services.",
              )}
            </p>
          ) : (
            <>
              <p>
                {t(
                  "Google grants read-only mailbox access. This app restricts reading to your selected label and never sends or changes email.",
                )}
              </p>
              <label className="check">
                <input
                  type="checkbox"
                  checked={mailConsent}
                  onChange={(e) => setMailConsent(e.target.checked)}
                />
                {t("I agree to connect Gmail for read-only job alerts.")}
              </label>
              <button
                disabled={!mailConsent || task.busy}
                onClick={() =>
                  void task.run(async () => {
                    const result = await api<{ url: string }>(
                      "/discovery/gmail/start",
                      "POST",
                      { source_id: source.id, reading_confirmed: true },
                    );
                    window.location.assign(result.url);
                  }, "")
                }
              >
                {t("Connect Gmail")}
              </button>
            </>
          )}
        </div>
      )}
      {available && (
        <details className="disclosure" open={!source.enabled || undefined}>
          <summary>{t("Review source settings")}</summary>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void task.run(async () => {
                await api(`/discovery/sources/${source.id}`, "PATCH", {
                  expected_version: source.version,
                  enabled: true,
                  terms_url: terms,
                  permission_note: note,
                  review_until: until,
                  access_confirmed: confirmed,
                  label_id: label,
                  label_name:
                    labels.find((item) => item.id === label)?.name ??
                    source.label_name,
                });
                setConfirmed(false);
                await refresh();
              }, t("Daily checking enabled."));
            }}
          >
            {source.provider === "gmail" && (
              <>
                <button
                  type="button"
                  disabled={task.busy}
                  onClick={() =>
                    void task.run(async () => {
                      setLabels(
                        await api(`/discovery/gmail/${source.id}/labels`),
                      );
                    }, "")
                  }
                >
                  {t("Load Gmail labels")}
                </button>
                <Field label={t("Job alerts label")}>
                  <select
                    required
                    value={label}
                    onChange={(e) => {
                      setLabel(e.target.value);
                      setConfirmed(false);
                    }}
                  >
                    <option value="">{t("Choose a custom label")}</option>
                    {label && !labels.some((item) => item.id === label) && (
                      <option value={label}>
                        {source.label_name || label}
                      </option>
                    )}
                    {labels.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </Field>
              </>
            )}
            <Field label={t("Terms or permission reference")}>
              <input
                type="url"
                required
                maxLength={2000}
                value={terms}
                onChange={(e) => {
                  setTerms(e.target.value);
                  setConfirmed(false);
                }}
                placeholder="https://…"
              />
            </Field>
            <Field label={t("Purpose and permission note")}>
              <textarea
                required
                maxLength={2000}
                value={note}
                onChange={(e) => {
                  setNote(e.target.value);
                  setConfirmed(false);
                }}
              />
            </Field>
            <Field label={t("Review valid until")}>
              <input
                type="date"
                required
                min={new Date(now).toISOString().slice(0, 10)}
                max={new Date(now + 90 * 86400000).toISOString().slice(0, 10)}
                value={until}
                onChange={(e) => {
                  setUntil(e.target.value);
                  setConfirmed(false);
                }}
              />
            </Field>
            <p className="muted">
              {t(
                "Review access at least every 90 days. Checks pause when this review expires.",
              )}
            </p>
            <label className="check">
              <input
                type="checkbox"
                required
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
              />
              {t(
                "I have reviewed access and authorise daily reading for this purpose.",
              )}
            </label>
            <button className="primary" disabled={task.busy}>
              {t("Enable daily checks")}
            </button>
          </form>
        </details>
      )}
      <details className="disclosure">
        <summary>{t("Check history and connection")}</summary>
        <button
          disabled={task.busy}
          onClick={() =>
            void task.run(async () => {
              setHistory(await api(`/discovery/sources/${source.id}/runs`));
            }, "")
          }
        >
          {t("Load check history")}
        </button>
        {history?.length === 0 && <p>{t("No checks yet.")}</p>}
        {history?.map((run) => (
          <p key={run.id}>
            {discoveryDate(run.started_at)} ·{" "}
            {run.status === "completed" || run.status === "unchanged"
              ? t("Checked successfully")
              : run.status === "running"
                ? t("In progress")
                : t("Check incomplete")}{" "}
            {run.error_code && sourceError(run.error_code)}
            {run.counts.new !== undefined &&
              ` · ${t("{0} new, {1} changed", [run.counts.new, run.counts.changed])}`}
          </p>
        ))}
        {source.provider === "gmail" && source.connected && (
          <>
            <label className="check">
              <input
                type="checkbox"
                checked={disconnecting}
                onChange={(e) => setDisconnecting(e.target.checked)}
              />
              {t(
                "Disconnect Gmail and remove saved access tokens. Keep imported alerts.",
              )}
            </label>
            <button
              disabled={task.busy || !disconnecting}
              onClick={() =>
                void task.run(async () => {
                  const result = await api<{ revoked: boolean }>(
                    `/discovery/gmail/${source.id}/disconnect`,
                    "POST",
                  );
                  await refresh();
                  if (!result.revoked)
                    throw new Error(
                      t(
                        "Local access was removed. Google revocation could not be confirmed; remove access in your Google account.",
                      ),
                    );
                }, t("Gmail disconnected."))
              }
            >
              {t("Disconnect Gmail")}
            </button>
          </>
        )}
      </details>
      {task.feedback}
    </article>
  );
}

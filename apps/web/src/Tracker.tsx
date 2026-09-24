import { t, localisedLabels, dateLocale } from "./i18n";
import { useEffect, useState } from "react";
import { api } from "./api";
import { optional, value } from "./forms";
import { useTask } from "./useTask";
import { ErrorState, Field, Loading } from "./ui";
import SubmissionPanel from "./SubmissionPanel";
type Application = {
  id: string;
  version: number;
  job_id: string;
  job_title: string | null;
  company_name: string | null;
  status: string;
  last_simulation?: { id: string };
  submission: {
    submitted_at: string;
    channel: string;
    receipt_ref: string;
  } | null;
  events: {
    id: string;
    to_status: string;
    at: string;
    note: string;
  }[];
};
const labels: Record<string, string> = localisedLabels({
  SHORTLISTED: "In shortlist",
  RESEARCHED: "Searched",
  SUBMITTED: "Manually submitted",
  INTERVIEWING: "In interview",
  OFFERED: "Offer received",
  REJECTED: "Rejected",
  WITHDRAWN: "Withdrawn",
  EXPIRED: "Expired",
});
const transitions: Record<string, string[]> = {
  SHORTLISTED: ["RESEARCHED", "SUBMITTED", "WITHDRAWN", "EXPIRED"],
  RESEARCHED: ["SUBMITTED", "WITHDRAWN", "EXPIRED"],
  SUBMITTED: ["INTERVIEWING", "OFFERED", "REJECTED", "WITHDRAWN"],
  INTERVIEWING: ["OFFERED", "REJECTED", "WITHDRAWN"],
  OFFERED: [],
  REJECTED: [],
  WITHDRAWN: [],
  EXPIRED: [],
};
export default function Tracker() {
  const [data, setData] = useState<{
    items: Application[];
    total: number;
  } | null>(null);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [offset, setOffset] = useState(0);
  useEffect(() => {
    let active = true;
    api<{
      items: Application[];
      total: number;
    }>(`/applications?limit=20&offset=${offset}`)
      .then((value) => {
        if (active) {
          setData(value);
          setError("");
        }
      })
      .catch((reason: Error) => {
        if (active) setError(reason.message);
      });
    return () => {
      active = false;
    };
  }, [refresh, offset]);
  return (
    <>
      <p className="eyebrow">{t("FOLLOW-UP")}</p>
      <h1>{t("Your applications")}</h1>
      <p>
        {t(
          "Track real applications or rehearse a final review locally. Employer submissions are still made outside this app.",
        )}
      </p>
      {error ? (
        <ErrorState error={error} retry={() => setRefresh(refresh + 1)} />
      ) : !data ? (
        <Loading />
      ) : (
        <>
          {!data.items.length && (
            <section className="empty">
              <h2>{t("Your shortlist is empty")}</h2>
              <p>{t("Add an opportunity from the analysis result.")}</p>
              <a href="#inbox">{t("Explore Inbox \u2192")}</a>
            </section>
          )}
          {data.items.map((item) => (
            <ApplicationCard
              key={item.id}
              item={item}
              changed={() => setRefresh(refresh + 1)}
            />
          ))}
          <div className="actions">
            <button
              disabled={!offset}
              onClick={() => setOffset(Math.max(0, offset - 20))}
            >
              {t("Previous")}
            </button>
            <button
              disabled={offset + 20 >= data.total}
              onClick={() => setOffset(offset + 20)}
            >
              {t("Next")}
            </button>
          </div>
        </>
      )}
    </>
  );
}
function ApplicationCard({
  item,
  changed,
}: {
  item: Application;
  changed: () => void;
}) {
  const [target, setTarget] = useState(transitions[item.status]?.[0] ?? "");
  const selectedTarget = transitions[item.status]?.includes(target)
    ? target
    : (transitions[item.status]?.[0] ?? "");
  const task = useTask();
  return (
    <article className="panel">
      <span className="tag">{labels[item.status]}</span>
      <h2>
        <a href={`#job/${item.job_id}`}>
          {item.job_title || t("Untitled opportunity")}
        </a>
      </h2>
      <p>{item.company_name || t("Company not provided")}</p>
      {item.last_simulation && (
        <p className="tag">{t("Local rehearsal completed")}</p>
      )}
      <SubmissionPanel
        applicationId={item.id}
        jobId={item.job_id}
        changed={changed}
        active={["SHORTLISTED", "RESEARCHED"].includes(item.status)}
      />
      <details>
        <summary>
          {t("Timeline (")}
          {item.events.length}
          {t(" events)")}
        </summary>
        <ol className="timeline">
          {item.events.map((event) => (
            <li key={event.id}>
              <strong>{labels[event.to_status]}</strong>
              <p>{new Date(event.at).toLocaleString(dateLocale())}</p>
              {event.note && <p>{event.note}</p>}
            </li>
          ))}
        </ol>
        {item.submission && (
          <p>
            {t("Submission recorded:")}{" "}
            {new Date(item.submission.submitted_at).toLocaleString(
              dateLocale(),
            )}{" "}
            · {item.submission.channel} · {item.submission.receipt_ref}
          </p>
        )}
      </details>
      {(transitions[item.status]?.length ?? 0) > 0 && (
        <details className="transition-form">
          <summary>{t("Record update")}</summary>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              const data = new FormData(event.currentTarget);
              void task.run(async () => {
                await api(`/applications/${item.id}/events`, "POST", {
                  expected_version: item.version,
                  to_status: selectedTarget,
                  note: value(data, "note"),
                  manual_confirmation: data.has("manual_confirmation"),
                  submitted_at: optional(data, "submitted_at")
                    ? new Date(value(data, "submitted_at")).toISOString()
                    : null,
                  channel: optional(data, "channel"),
                  receipt_ref: optional(data, "receipt_ref"),
                });
                changed();
              }, t("Event recorded."));
            }}
          >
            <Field label={t("New state")}>
              <select
                value={selectedTarget}
                onChange={(event) => setTarget(event.target.value)}
              >
                {transitions[item.status]?.map((state) => (
                  <option key={state} value={state}>
                    {labels[state]}
                  </option>
                ))}
              </select>
            </Field>
            <Field label={t("Update note")}>
              <textarea name="note" maxLength={3000} rows={2} />
            </Field>
            {selectedTarget === "SUBMITTED" && (
              <fieldset>
                <legend>{t("Manual submission record")}</legend>
                <Field label={t("Date and time of submission")}>
                  <input type="datetime-local" name="submitted_at" required />
                </Field>
                <Field label={t("Channel used")}>
                  <input
                    name="channel"
                    required
                    placeholder={t("E.g.: company portal")}
                  />
                </Field>
                <Field label={t("Supporting record reference")}>
                  <input
                    name="receipt_ref"
                    required
                    placeholder={t(
                      "E.g.: confirmation received / process number",
                    )}
                  />
                </Field>
                <label className="check">
                  <input type="checkbox" name="manual_confirmation" required />
                  {t(
                    "I confirm that I have already submitted this application outside the app.",
                  )}
                </label>
              </fieldset>
            )}
            {task.feedback}
            <button className="primary" disabled={task.busy}>
              {t("Save update")}
            </button>
          </form>
        </details>
      )}
    </article>
  );
}

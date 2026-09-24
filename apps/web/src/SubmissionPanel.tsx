import { useState } from "react";
import { api } from "./api";
import { dateLocale, localisedLabels, t } from "./i18n";
import { useTask } from "./useTask";

type PackageChoice = {
  id: string;
  version: number;
  status: string;
  stale: boolean;
};
export type Submission = {
  id: string;
  version: number;
  status: string;
  payload_hash: string;
  payload: {
    package_id: string;
    package_version: number;
    recipient: string;
    content: {
      name: string;
      contact_lines: string[];
      job_title: string;
      company_name: string;
      cv: string[];
      cover_letter: string[];
      answers: { question: string; text: string }[];
    };
  };
  authorisation: { expires_at: string } | null;
  receipt: { id: string; accepted_at: string; payload_hash: string } | null;
  history: { status: string; at: string; attempt_id: string | null }[];
};
const statuses: Record<string, string> = localisedLabels({
  NEEDS_REVIEW: "Ready for your review",
  APPROVED: "Authorised for a local rehearsal",
  DISPATCHING: "Attempt started — check its result",
  UNKNOWN: "Result uncertain — check before continuing",
  FAILED: "No receipt found — fresh authorisation required",
  CANCELLED: "Rehearsal cancelled",
  SIMULATED: "Rehearsal completed — nothing sent to an employer",
});

export default function SubmissionPanel({
  applicationId,
  jobId,
  changed,
}: {
  applicationId: string;
  jobId: string;
  changed: () => void;
}) {
  const task = useTask();
  const [opened, setOpened] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [packages, setPackages] = useState<PackageChoice[]>([]);
  const [packageId, setPackageId] = useState("");
  const [workflow, setWorkflow] = useState<Submission | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [refreshRequired, setRefreshRequired] = useState(false);
  const uncertain =
    workflow && ["DISPATCHING", "UNKNOWN"].includes(workflow.status);
  const finished = workflow?.status === "SIMULATED";
  const canPrepare = !uncertain && !finished;
  async function refresh() {
    const [current, choices] = await Promise.all([
      api<Submission | null>(`/applications/${applicationId}/submission`),
      api<PackageChoice[]>(`/jobs/${jobId}/packages`),
    ]);
    setWorkflow(current);
    const approved = choices.filter((p) => p.status === "APPROVED" && !p.stale);
    setPackages(approved);
    setPackageId(
      current && approved.some((p) => p.id === current.payload.package_id)
        ? current.payload.package_id
        : (approved[0]?.id ?? ""),
    );
    setConfirmed(false);
    setRefreshRequired(false);
    setLoaded(true);
  }
  async function act(verb: string) {
    if (!workflow) return;
    try {
      const result = await api<Submission>(
        `/submissions/${workflow.id}/${verb}`,
        "POST",
        {
          expected_version: workflow.version,
          ...(verb === "authorise"
            ? {
                payload_hash: workflow.payload_hash,
                submission_confirmed: confirmed,
              }
            : {}),
        },
      );
      setWorkflow(result);
      setConfirmed(false);
      if (result.status === "SIMULATED") changed();
    } catch (error) {
      // A lost response may follow a committed write; reload before another action.
      setRefreshRequired(true);
      setConfirmed(false);
      throw error;
    }
  }
  const content = workflow?.payload.content;
  return (
    <section className="submission-panel">
      <button
        aria-expanded={opened}
        disabled={task.busy}
        onClick={() => {
          setOpened(!opened);
          if (!opened) void task.run(refresh, "");
        }}
      >
        {t("Rehearse application")}
      </button>
      {opened && (
        <div className="review-callout">
          <h3>{t("Local application rehearsal")}</h3>
          <p>
            {t(
              "Practise the final review safely. This channel stays on your computer and never contacts an employer.",
            )}
          </p>
          {task.feedback}
          <button
            disabled={task.busy}
            onClick={() => void task.run(refresh, t("Rehearsal reloaded."))}
          >
            {t("Refresh rehearsal")}
          </button>
          {refreshRequired && (
            <p role="alert">
              {t(
                "Reload the rehearsal to check what was saved before continuing.",
              )}
            </p>
          )}
          {loaded && (
            <>
              {canPrepare && (
                <>
                  {packages.length ? (
                    <>
                      <label>
                        {t("Approved document package")}
                        <select
                          value={packageId}
                          disabled={task.busy}
                          onChange={(e) => {
                            setPackageId(e.target.value);
                            setConfirmed(false);
                          }}
                        >
                          {packages.map((p, index) => (
                            <option key={p.id} value={p.id}>
                              {t("Package {0} · revision {1}", [
                                index + 1,
                                p.version,
                              ])}
                            </option>
                          ))}
                        </select>
                      </label>
                      <button
                        disabled={task.busy || refreshRequired || !packageId}
                        onClick={() =>
                          void task.run(async () => {
                            const selected = packages.find(
                              (p) => p.id === packageId,
                            )!;
                            try {
                              setWorkflow(
                                await api<Submission>(
                                  `/applications/${applicationId}/submission`,
                                  "POST",
                                  {
                                    package_id: selected.id,
                                    package_version: selected.version,
                                  },
                                ),
                              );
                              setConfirmed(false);
                            } catch (error) {
                              setRefreshRequired(true);
                              throw error;
                            }
                          }, t("Review the content below before authorising."))
                        }
                      >
                        {t("Prepare final review")}
                      </button>
                    </>
                  ) : (
                    <p>
                      {t(
                        "Approve a current document package and review the vacancy analysis first.",
                      )}
                    </p>
                  )}
                  <p>
                    <a href={`#job/${jobId}`}>
                      {t("Review vacancy and documents")}
                    </a>
                  </p>
                </>
              )}
              {workflow && content && (
                <>
                  <p role="status">
                    <strong>{statuses[workflow.status]}</strong>
                  </p>
                  <p>{t("Recipient: local sandbox only")}</p>
                  <p>
                    {content.job_title} · {content.company_name}
                  </p>
                  <details open={!finished}>
                    <summary>{t("Content included in this rehearsal")}</summary>
                    <p>{content.name}</p>
                    {content.contact_lines.map((line, i) => (
                      <p key={i}>{line}</p>
                    ))}
                    <h4>{t("CV")}</h4>
                    {content.cv.map((line, i) => (
                      <p key={i}>{line}</p>
                    ))}
                    <h4>{t("Cover letter claims")}</h4>
                    {content.cover_letter.map((line, i) => (
                      <p key={i}>{line}</p>
                    ))}
                    {content.answers.map((a, i) => (
                      <div key={i}>
                        <h4>{a.question}</h4>
                        <p className="preserve">{a.text}</p>
                      </div>
                    ))}
                  </details>
                  {workflow.authorisation && (
                    <p>
                      {t("Authorisation expires at {0}.", [
                        new Date(
                          workflow.authorisation.expires_at,
                        ).toLocaleString(dateLocale()),
                      ])}
                    </p>
                  )}
                  {!uncertain &&
                    !finished &&
                    workflow.status !== "CANCELLED" && (
                      <>
                        <label className="check">
                          <input
                            type="checkbox"
                            checked={confirmed}
                            disabled={task.busy || refreshRequired}
                            onChange={(e) => setConfirmed(e.target.checked)}
                          />
                          {t(
                            "I reviewed this content and authorise this local simulation only.",
                          )}
                        </label>
                        <div className="actions">
                          <button
                            disabled={
                              task.busy ||
                              refreshRequired ||
                              !confirmed ||
                              packageId !== workflow.payload.package_id
                            }
                            onClick={() =>
                              void task.run(
                                () => act("authorise"),
                                t(
                                  "Authorised for 15 minutes. You can now run the rehearsal.",
                                ),
                              )
                            }
                          >
                            {t("Authorise rehearsal")}
                          </button>
                          {workflow.status === "APPROVED" && (
                            <button
                              className="primary"
                              disabled={
                                task.busy ||
                                refreshRequired ||
                                packageId !== workflow.payload.package_id
                              }
                              onClick={() =>
                                void task.run(() => act("execute"), "")
                              }
                            >
                              {t("Run local rehearsal")}
                            </button>
                          )}
                          <button
                            disabled={task.busy || refreshRequired}
                            onClick={() =>
                              void task.run(() => act("cancel"), "")
                            }
                          >
                            {t("Cancel rehearsal")}
                          </button>
                        </div>
                      </>
                    )}
                  {uncertain && (
                    <>
                      <p>
                        {t(
                          "Check the stored receipt before trying again. This action does not resend the payload.",
                        )}
                      </p>
                      <button
                        className="primary"
                        disabled={task.busy || refreshRequired}
                        onClick={() =>
                          void task.run(() => act("reconcile"), "")
                        }
                      >
                        {t("Check attempt result")}
                      </button>
                    </>
                  )}
                  {workflow.receipt && (
                    <div className="document-preview">
                      <h4>{t("Simulated receipt")}</h4>
                      <p className="preserve">{workflow.receipt.id}</p>
                      <p>
                        {new Date(workflow.receipt.accepted_at).toLocaleString(
                          dateLocale(),
                        )}
                      </p>
                      <p>
                        {t("Your real application status has not changed.")}
                      </p>
                    </div>
                  )}
                  <details>
                    <summary>{t("Rehearsal history and verification")}</summary>
                    <p className="preserve">
                      {t("Payload SHA-256")}: {workflow.payload_hash}
                    </p>
                    <ol className="timeline">
                      {workflow.history.map((event, i) => (
                        <li key={i}>
                          {statuses[event.status]} ·{" "}
                          {new Date(event.at).toLocaleString(dateLocale())}
                        </li>
                      ))}
                    </ol>
                  </details>
                </>
              )}
            </>
          )}
        </div>
      )}
    </section>
  );
}

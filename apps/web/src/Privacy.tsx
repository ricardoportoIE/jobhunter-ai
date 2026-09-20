import { t } from "./i18n";
import { api } from "./api";
import { useTask } from "./useTask";
export default function Privacy() {
  const task = useTask();
  return (
    <>
      <p className="eyebrow">{t("YOUR DATA")}</p>
      <h1>{t("Privacy and history")}</h1>
      <section className="panel narrow">
        <h2>{t("Export application data")}</h2>
        <p>
          {t(
            "The file includes profile, facts, evidence, vacancies, analyses, applications, change history, AI suggestions and search index. Keep it in a private location.",
          )}
        </p>
        {task.feedback}
        <button
          className="primary"
          disabled={task.busy}
          onClick={() => {
            void task.run(async () => {
              const data = await api<unknown>("/candidate/export");
              const url = URL.createObjectURL(
                new Blob([JSON.stringify(data, null, 2)], {
                  type: "application/json",
                }),
              );
              const link = document.createElement("a");
              link.href = url;
              link.download = "jobhunter-export.json";
              link.click();
              setTimeout(() => URL.revokeObjectURL(url), 1000);
            }, t("Export prepared."));
          }}
        >
          {t("Download export")}
        </button>
      </section>
      <section className="panel narrow">
        <h2>{t("Processing by OpenAI")}</h2>
        <p>
          {t(
            "Extracting a vacancy sends its text to OpenAI. CV extraction sends the text from your chosen file after consent. Matching and search send only the text you authorise. The API key remains in the backend.",
          )}
        </p>
        <p>
          {t(
            "Response storage is disabled. This does not eliminate possible content retention in abuse monitoring logs for up to 30 days. This setting does not imply data residency in Europe.",
          )}
        </p>
        <a
          href="https://developers.openai.com/api/docs/guides/your-data"
          target="_blank"
          rel="noopener noreferrer"
        >
          {t("Consult OpenAI data controls \u2197")}
        </a>
      </section>
      <section className="panel narrow">
        <h2>{t("Delete local data")}</h2>
        <p>
          {t(
            "Complete deletion, including snapshots and audit, is a local administrative operation described in the project guide. It closes all sessions and preserves the access account.",
          )}
        </p>
        <p>
          {t(
            "Removing a fact or evidence from the screen invalidates analyses but keeps previous versions in the history. The administrative command deletes these records from the database. Source documents and exports saved outside the application need to be handled separately.",
          )}
        </p>
        <p>
          {t(
            "Cost totals without personal linkage are preserved so that deletion does not reset the monthly budget. Local deletion does not erase data already processed by the provider.",
          )}
        </p>
      </section>
    </>
  );
}

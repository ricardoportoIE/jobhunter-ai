import { t } from "./i18n";
import { api } from "./api";
import type { Match } from "./types";
import { useTask } from "./useTask";
export default function ShortlistButton({ match }: { match: Match }) {
  const task = useTask();
  return (
    <div className="review-callout">
      <p>
        {t(
          "Adding to shortlist registers your interest. The application decision remains under your control.",
        )}
      </p>
      {task.feedback}
      <button
        className="primary"
        disabled={task.busy || match.stale}
        onClick={() => {
          void task.run(async () => {
            await api("/applications", "POST", {
              job_id: match.job_id,
              match_id: match.id,
            });
          }, t("Added to shortlist."));
        }}
      >
        {t("Add to shortlist")}
      </button>{" "}
      <a href="#tracker">{t("View applications \u2192")}</a>
    </div>
  );
}

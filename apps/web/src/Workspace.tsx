import { t } from "./i18n";
import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { ImportJob, Inbox } from "./Inbox";
import JobDetail from "./JobDetail";
import ProfilePage from "./ProfilePage";
import Tracker from "./Tracker";
import Privacy from "./Privacy";
import { AiActivity } from "./AiTools";
import SemanticSearch from "./SemanticSearch";
import type { Evidence, Fact, Profile } from "./types";
import { ErrorState, Loading } from "./ui";
async function loadProfile() {
  const [profile, facts, evidence] = await Promise.all([
    api<Profile>("/candidate/profile"),
    api<Fact[]>("/candidate/facts"),
    api<Evidence[]>("/candidate/evidence"),
  ]);
  return { profile, facts, evidence };
}
export default function Workspace() {
  const [route, setRoute] = useState(window.location.hash.slice(1) || "inbox");
  const [data, setData] = useState<{
    profile: Profile;
    facts: Fact[];
    evidence: Evidence[];
  } | null>(null);
  const [error, setError] = useState("");
  const refresh = useCallback(async () => {
    setData(await loadProfile());
    setError("");
  }, []);
  useEffect(() => {
    let active = true;
    loadProfile()
      .then((value) => {
        if (active) setData(value);
      })
      .catch((reason: Error) => {
        if (active) setError(reason.message);
      });
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    const changed = () => {
      setRoute(window.location.hash.slice(1) || "inbox");
    };
    window.addEventListener("hashchange", changed);
    return () => window.removeEventListener("hashchange", changed);
  }, []);
  useEffect(() => {
    document.getElementById("workspace-main")?.focus();
  }, [route]);
  return (
    <div className="app-layout">
      <a
        className="skip-link"
        href="#workspace-main"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById("workspace-main")?.focus();
        }}
      >
        {t("Go to content")}
      </a>
      <aside className="sidebar">
        <a className="brand" href="#inbox">
          <span className="brand-mark" aria-hidden="true">
            jh
          </span>
          <span>
            JobHunter <span className="brand-ai">AI</span>
          </span>
        </a>
        <p className="eyebrow">{t("WORKSPACE")}</p>
        <nav aria-label={t("Main navigation")}>
          <a
            href="#inbox"
            aria-current={route === "inbox" ? "page" : undefined}
          >
            {t("Opportunities Inbox")}
          </a>
          <a
            href="#profile"
            aria-current={route === "profile" ? "page" : undefined}
          >
            {t("Profile and evidence")}
          </a>
          <a
            href="#tracker"
            aria-current={route === "tracker" ? "page" : undefined}
          >
            {t("Applications")}
          </a>
          <a
            href="#import"
            aria-current={route === "import" ? "page" : undefined}
          >
            {t("Import vacancy")}
          </a>
          <a
            href="#privacy"
            aria-current={route === "privacy" ? "page" : undefined}
          >
            {t("Privacy")}
          </a>
          <a
            href="#search"
            aria-current={route === "search" ? "page" : undefined}
          >
            {t("Semantic search")}
          </a>
          <a href="#ai" aria-current={route === "ai" ? "page" : undefined}>
            {t("AI activity")}
          </a>
        </nav>
        <p className="sidebar-note">
          {t("You decide every step.")}
          <br />
          {t("Local data; AI under your command.")}
        </p>
      </aside>
      <main id="workspace-main" tabIndex={-1} className="app-main">
        {error ? (
          <ErrorState
            error={error}
            retry={() => {
              void refresh().catch((reason: Error) => setError(reason.message));
            }}
          />
        ) : !data ? (
          <Loading />
        ) : route === "profile" ? (
          <ProfilePage {...data} refresh={refresh} />
        ) : route === "privacy" ? (
          <Privacy />
        ) : route === "ai" ? (
          <AiActivity />
        ) : route === "search" ? (
          <SemanticSearch facts={data.facts} />
        ) : route === "tracker" ? (
          <Tracker />
        ) : route === "import" ? (
          <ImportJob />
        ) : route.startsWith("job/") ? (
          <JobDetail
            key={route}
            id={route.slice(4)}
            profile={data.profile}
            facts={data.facts}
          />
        ) : (
          <Inbox />
        )}
      </main>
    </div>
  );
}

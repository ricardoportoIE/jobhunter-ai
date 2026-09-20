import { t, localisedLabels } from "./i18n";
import { useEffect, useState } from "react";
import { isWorkspaceReady } from "./health";
type Connection = "checking" | "ready" | "unavailable";
const messages = localisedLabels({
  checking: {
    title: "Checking connection",
    detail: "Connecting to local environment\u2026",
  },
  ready: {
    title: "Connected environment",
    detail: "The API and database are responding.",
  },
  unavailable: {
    title: "Connection unavailable",
    detail: "Check local services and try again.",
  },
});
export default function App() {
  const [connection, setConnection] = useState<Connection>("checking");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => {
      controller.abort();
      setConnection("unavailable");
    }, 8000);
    isWorkspaceReady(controller.signal)
      .then((ready) => {
        if (!controller.signal.aborted)
          setConnection(ready ? "ready" : "unavailable");
      })
      .catch(() => {
        if (!controller.signal.aborted) setConnection("unavailable");
      })
      .finally(() => window.clearTimeout(timeout));
    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [attempt]);
  return (
    <div className="workspace">
      <header className="topbar">
        <a className="brand" href="/" aria-label={t("JobHunter AI, home")}>
          <span className="brand-mark" aria-hidden="true">
            jh
          </span>
          <span>
            JobHunter <span className="brand-ai">AI</span>
          </span>
        </a>
        <span className="local-label">
          <span aria-hidden="true" />
          {t(" Local environment")}
        </span>
      </header>

      <main id="main-content">
        <div className="intro">
          <p className="eyebrow">{t("YOUR WORKSPACE")}</p>
          <h1>
            {t("A job search")}
            <br />
            {t("evidence-based.")}
          </h1>
          <p className="lead">
            {t(
              "Organise your profile, understand opportunities and prepare applications with decisions under your control.",
            )}
          </p>
        </div>

        <section
          className="connection-panel"
          aria-labelledby="connection-heading"
        >
          <div className={`connection-icon ${connection}`} aria-hidden="true">
            {connection === "ready"
              ? "✓"
              : connection === "checking"
                ? "·"
                : "!"}
          </div>
          <div className="connection-copy" role="status" aria-live="polite">
            <h2 id="connection-heading">{messages[connection].title}</h2>
            <p>{messages[connection].detail}</p>
          </div>
          <button
            disabled={connection === "checking"}
            onClick={() => {
              setConnection("checking");
              setAttempt((value) => value + 1);
            }}
          >
            {t("Check connection ")}
            <span aria-hidden="true">↗</span>
          </button>
        </section>

        <section className="foundation" aria-labelledby="foundation-heading">
          <div className="section-heading">
            <h2 id="foundation-heading">
              {t("Your workspace is taking shape")}
            </h2>
            <span className="phase-label">P1-01</span>
          </div>
          <ol className="steps">
            <li>
              <span className="step-number current">01</span>
              <div>
                <h3>{t("Local environment")}</h3>
                <p>
                  {t(
                    "Interface, API and database connected in a single space.",
                  )}
                </p>
                <span className="step-tag">{t("Current stage")}</span>
              </div>
            </li>
            <li>
              <span className="step-number">02</span>
              <div>
                <h3>{t("Access and profile")}</h3>
                <p>
                  {t(
                    "Authenticated session and facts linked to your evidence.",
                  )}
                </p>
                <span className="step-tag muted">{t("Upcoming features")}</span>
              </div>
            </li>
            <li>
              <span className="step-number">03</span>
              <div>
                <h3>{t("First opportunity")}</h3>
                <p>{t("Vacancy import, compatibility and gap analysis.")}</p>
                <span className="step-tag muted">{t("Planned")}</span>
              </div>
            </li>
          </ol>
        </section>

        <aside className="notice">
          <span aria-hidden="true">↳</span>
          <p>
            {t(
              "This is the initial project structure. Your private profile is not yet available in the app and no application is sent.",
            )}
          </p>
        </aside>
      </main>
      <footer>
        <span>
          JobHunter AI <span className="footer-separator">/</span>{" "}
          {t("Local development")}
        </span>
        <a href="/api/docs">
          {t("API documentation ")}
          <span aria-hidden="true">↗</span>
        </a>
      </footer>
    </div>
  );
}

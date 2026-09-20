import { useEffect, useState, type FormEvent } from "react";
import Workspace from "./Workspace";
import { api, ApiError, setSession, type Session } from "./api";
import LanguageSelector from "./LanguageSelector";
import { useLocale, t } from "./i18n";
export default function App() {
  useLocale();
  const [session, updateSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const expired = () => {
      setSession(null);
      updateSession(null);
      setError(t("Session expired. Please log in again."));
    };
    window.addEventListener("session-expired", expired);
    return () => window.removeEventListener("session-expired", expired);
  }, []);
  useEffect(() => {
    api<Session>("/session")
      .then((value) => {
        setSession(value);
        updateSession(value);
      })
      .catch((reason: unknown) => {
        if (!(reason instanceof ApiError && reason.status === 401))
          setError(t("Service unavailable. Please try logging in again."));
      })
      .finally(() => setLoading(false));
  }, []);
  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    const form = new FormData(event.currentTarget);
    try {
      const value = await api<Session>("/session", "POST", {
        username: form.get("username"),
        password: form.get("password"),
      });
      setSession(value);
      updateSession(value);
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : t("Error logging in."),
      );
    } finally {
      setBusy(false);
    }
  }
  if (loading)
    return (
      <main className="login">
        <LanguageSelector />
        <p role="status">{t("Checking session\u2026")}</p>
      </main>
    );
  if (!session)
    return (
      <main className="login">
        <LanguageSelector />
        <p className="eyebrow">JOBHUNTER AI · LOCAL</p>
        <h1>
          {t("Your next step")}
          <br />
          {t("starts here.")}
        </h1>
        <p>
          {t(
            "Log in to organise your profile and assess opportunities with evidence.",
          )}
        </p>
        <form
          onSubmit={(event) => {
            void login(event);
          }}
        >
          <label>
            {t("User")}
            <input
              name="username"
              autoComplete="username"
              required
              defaultValue="local"
            />
          </label>
          <label>
            {t("Password")}
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              required
              maxLength={256}
            />
          </label>
          {error && <p role="alert">{t(error)}</p>}
          <button disabled={busy}>
            {busy ? t("Logging in\u2026") : t("Log in")}
          </button>
        </form>
        <p className="muted">
          {t("Use the credential created in local setup.")}
        </p>
      </main>
    );
  return (
    <>
      <div className="session-bar">
        <LanguageSelector />
        <span>{t("Active local session")}</span>
        <button
          onClick={() => {
            void api("/session", "DELETE")
              .then(() => {
                setSession(null);
                updateSession(null);
              })
              .catch(() => setError(t("Could not log out. Please try again.")));
          }}
        >
          {t("Log out")}
        </button>
        {error && <span role="alert">{t(error)}</span>}
      </div>
      <Workspace />
    </>
  );
}

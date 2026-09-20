import { t } from "./i18n";
import { useState } from "react";
export function useTask() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  async function run(
    action: () => Promise<void>,
    message = t("Change saved."),
  ) {
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      await action();
      setSuccess(message);
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : t("Operation failed."),
      );
    } finally {
      setBusy(false);
    }
  }
  return {
    busy,
    error,
    run,
    feedback: (
      <>
        {error && <p role="alert">{t(error)}</p>}
        {success && <p role="status">{t(success)}</p>}
      </>
    ),
  };
}

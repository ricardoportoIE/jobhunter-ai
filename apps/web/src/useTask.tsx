import { useState } from "react";

export function useTask() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  async function run(
    action: () => Promise<void>,
    message = "Alteração salva.",
  ) {
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      await action();
      setSuccess(message);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Falha na operação.");
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
        {error && <p role="alert">{error}</p>}
        {success && <p role="status">{success}</p>}
      </>
    ),
  };
}

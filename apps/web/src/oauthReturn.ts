type OAuthReturn = { code: string; state: string; error: boolean };
let pending: OAuthReturn | null = null;

export function captureOAuthReturn() {
  const query = new URLSearchParams(window.location.search);
  if (!query.has("state") || (!query.has("code") && !query.has("error")))
    return;
  pending = {
    code: query.get("code") ?? "",
    state: query.get("state") ?? "",
    error: query.has("error"),
  };
  window.history.replaceState(null, "", `${window.location.pathname}#discover`);
}

export function takeOAuthReturn() {
  const value = pending;
  pending = null;
  return value;
}

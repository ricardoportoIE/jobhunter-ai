import { t } from "./i18n";
export type Session = {
  user_id: string;
  csrf_token: string;
};
let csrf = "";
export function setSession(session: Session | null) {
  csrf = session?.csrf_token ?? "";
}
export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}
export async function api<T>(
  path: string,
  method = "GET",
  data?: unknown,
  extra?: Record<string, string>,
): Promise<T> {
  const binary = data instanceof Blob;
  const options: RequestInit = {
    method,
    credentials: "same-origin",
    cache: "no-store",
    headers: {
      ...(data === undefined
        ? {}
        : {
            "Content-Type": binary
              ? "application/octet-stream"
              : "application/json",
          }),
      ...(method === "GET" ? {} : { "X-CSRF-Token": csrf }),
      ...extra,
    },
    body: data === undefined ? undefined : binary ? data : JSON.stringify(data),
  };
  const connectionError = () =>
    new ApiError(
      0,
      t(
        "Connection lost. Check the local service and try again. Your input remains on this screen.",
      ),
    );
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, options);
  } catch {
    // A failed read is safe to retry once. Never replay a write or paid AI operation.
    if (method !== "GET") throw connectionError();
    try {
      response = await fetch(`/api/v1${path}`, options);
    } catch {
      throw connectionError();
    }
  }
  if (!response.ok) {
    if (response.status === 401 && path !== "/session")
      window.dispatchEvent(new Event("session-expired"));
    const body: unknown = await response.json().catch(() => null);
    const message =
      body && typeof body === "object" && "error" in body
        ? (
            body as {
              error: {
                message?: string;
              };
            }
          ).error.message
        : undefined;
    throw new ApiError(
      response.status,
      message ? t(message) : t("Could not complete. Please try again."),
    );
  }
  return response.status === 204
    ? (undefined as T)
    : ((await response.json()) as T);
}

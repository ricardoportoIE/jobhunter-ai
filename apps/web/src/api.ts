export type Session = { user_id: string; csrf_token: string };
let csrf = '';
export function setSession(session: Session | null) { csrf = session?.csrf_token ?? ''; }
export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) { super(message); this.status = status; }
}
export async function api<T>(path: string, method = 'GET', data?: unknown, extra?: Record<string, string>): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    method, credentials: 'same-origin', cache: 'no-store',
    headers: { ...(data === undefined ? {} : { 'Content-Type': 'application/json' }),
      ...(method === 'GET' ? {} : { 'X-CSRF-Token': csrf }), ...extra },
    body: data === undefined ? undefined : JSON.stringify(data),
  });
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const message = body && typeof body === 'object' && 'error' in body
      ? (body as { error: { message?: string } }).error.message : undefined;
    throw new ApiError(response.status, message || 'Não foi possível concluir. Tente novamente.');
  }
  return response.status === 204 ? undefined as T : await response.json() as T;
}

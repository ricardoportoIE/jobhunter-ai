export async function isWorkspaceReady(signal: AbortSignal): Promise<boolean> {
  const response = await fetch('/api/health/ready', { signal, cache: 'no-store' });
  if (!response.ok) return false;
  const body: unknown = await response.json();
  return typeof body === 'object' && body !== null && 'status' in body
    && body.status === 'ready' && 'checks' in body
    && typeof body.checks === 'object' && body.checks !== null
    && 'database' in body.checks && body.checks.database === 'ok';
}

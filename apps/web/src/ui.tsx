import type { ReactNode } from "react";

export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label>
      {label}
      {children}
    </label>
  );
}
export function Loading() {
  return <p role="status">Carregando…</p>;
}
export function ErrorState({
  error,
  retry,
}: {
  error: string;
  retry: () => void;
}) {
  return (
    <div role="alert">
      <p>{error}</p>
      <button onClick={retry}>Tentar novamente</button>
    </div>
  );
}

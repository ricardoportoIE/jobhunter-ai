import { t } from "./i18n";
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
  return <p role="status">{t("Loading\u2026")}</p>;
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
      <p>{t(error)}</p>
      <button onClick={retry}>{t("Try again")}</button>
    </div>
  );
}

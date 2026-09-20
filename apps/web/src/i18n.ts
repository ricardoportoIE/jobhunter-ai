import { useSyncExternalStore } from "react";
import portuguese from "./locales/pt.json";

export type Locale = "en-GB" | "pt";
const storageKey = "jobhunter.locale";
const translations: Record<string, string> = portuguese;
const listeners = new Set<() => void>();
const reverse = Object.fromEntries(
  Object.entries(translations).map(([key, value]) => [value, key]),
);
function initialLocale(): Locale {
  try {
    return localStorage.getItem(storageKey) === "pt" ? "pt" : "en-GB";
  } catch {
    return "en-GB";
  }
}
let current = initialLocale();
export const getLocale = () => current;
export const dateLocale = () => (current === "pt" ? "pt-PT" : "en-GB");
export function setLocale(locale: Locale) {
  current = locale;
  document.documentElement.lang = locale === "pt" ? "pt" : "en-GB";
  try {
    localStorage.setItem(storageKey, locale);
  } catch {
    /* Storage may be disabled. */
  }
  listeners.forEach((listener) => listener());
}
function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
export const useLocale = () =>
  useSyncExternalStore(subscribe, getLocale, () => "en-GB" as Locale);
/** Translate known system prefixes, preserving the evidence text that follows. */
export function systemMessage(message: string): string {
  for (const prefix of [
    "Disqualifying requirement not yet confirmed: ",
    "Requisito eliminatório ainda não confirmado: ",
    "A avaliação positiva não tem fatos válidos para matching. ",
  ]) {
    if (message.startsWith(prefix))
      return t(prefix) + message.slice(prefix.length);
  }
  return t(message);
}
export function t(message: string, values: readonly unknown[] = []): string {
  const clean = message.trim();
  const key = Object.hasOwn(translations, clean)
    ? clean
    : (reverse[clean] ?? clean);
  const text = current === "pt" ? (translations[key] ?? key) : key;
  const result = text.replace(/\{(\d+)\}/g, (token, index: string) =>
    Number(index) < values.length ? String(values[Number(index)] ?? "") : token,
  );
  return (
    message.slice(0, message.indexOf(clean)) +
    result +
    message.slice(message.indexOf(clean) + clean.length)
  );
}

/** Resolve shared labels at render time, without changing their stable data keys. */
export function localisedLabels<T extends object>(labels: T): T {
  return new Proxy(labels, {
    get(target, property, receiver) {
      const value: unknown = Reflect.get(target, property, receiver);
      return typeof value === "string" ? t(value) : value;
    },
  });
}

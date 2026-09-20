import { setLocale, t, useLocale, type Locale } from "./i18n";

export default function LanguageSelector() {
  const locale = useLocale();
  return (
    <label className="language-selector">
      <span aria-hidden="true">◎</span> {t("Language")}
      <select
        aria-label={t("Language")}
        value={locale}
        onChange={(event) => setLocale(event.target.value as Locale)}
      >
        <option value="en-GB">English (UK)</option>
        <option value="pt">Português</option>
      </select>
    </label>
  );
}

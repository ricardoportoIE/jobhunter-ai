import { t } from "./i18n";
import { useEffect, useState } from "react";
import { api } from "./api";
import type { Fact, Profile } from "./types";
import { Field } from "./ui";
import { useTask } from "./useTask";
type DraftFact = {
  claim: string;
  category: Fact["category"];
  quote: string;
  sensitivity: "private" | "sensitive";
};
type Draft = Omit<Profile, "status"> & {
  status: "draft" | "applied";
  filename: string;
  source_text: string;
  facts: DraftFact[];
  warnings: string[];
};
const categories: DraftFact["category"][] = [
  "skill",
  "experience",
  "education",
  "project",
  "certification",
  "achievement",
  "preference",
  "constraint",
];
const uses = ["matching", "cv", "cover_letter", "application_form"] as const;
export default function CvImport({
  profile,
  refresh,
}: {
  profile: Profile;
  refresh: () => Promise<void>;
}) {
  const task = useTask();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [savedDrafts, setSavedDrafts] = useState<Draft[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [consent, setConsent] = useState(false);
  const [reviewed, setReviewed] = useState(false);
  const [allowed, setAllowed] = useState<string[]>([
    "matching",
    "cv",
    "cover_letter",
  ]);
  const [loadError, setLoadError] = useState(false);
  const loadDrafts = () =>
    api<Draft[]>("/candidate/cv/drafts").then((items) => {
      setSavedDrafts(items);
      setLoadError(false);
    });
  useEffect(() => {
    let active = true;
    api<Draft[]>("/candidate/cv/drafts")
      .then((items) => {
        if (active) setSavedDrafts(items);
      })
      .catch(() => {
        if (active) setLoadError(true);
      });
    return () => {
      active = false;
    };
  }, []);
  function change(value: Partial<Draft>) {
    if (draft) {
      setDraft({ ...draft, ...value });
      setReviewed(false);
    }
  }
  async function saveDraft() {
    if (!draft) throw new Error(t("Choose a draft first."));
    const result = await api<Draft>(
      `/candidate/cv/drafts/${draft.id}`,
      "PATCH",
      {
        expected_version: draft.version,
        display_name: draft.display_name,
        target_roles: draft.target_roles,
        locations: draft.locations,
        markets: draft.markets,
        work_modes: draft.work_modes,
        facts: draft.facts,
      },
    );
    setDraft(result);
    return result;
  }
  return (
    <section className="panel cv-import">
      <h2>{t("Start with your CV")}</h2>
      <p>
        {t(
          "Upload a PDF or Word .docx to prepare your profile and evidence. Review, add, edit or remove suggestions before applying them. Existing facts are preserved.",
        )}
      </p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void task.run(async () => {
            if (!file || !consent)
              throw new Error(
                t("Choose a CV and confirm AI processing first."),
              );
            if (file.size > 4 * 1024 * 1024)
              throw new Error(t("The CV must be no larger than 4 MiB."));
            const result = await api<Draft>(
              "/candidate/cv/extract",
              "POST",
              file,
              {
                "X-CV-Filename": encodeURIComponent(file.name),
                "X-AI-Consent": "true",
              },
            );
            if (result.status === "applied")
              throw new Error(
                t(
                  "This CV has already been imported. Edit your existing profile and facts below.",
                ),
              );
            setDraft(result);
            setReviewed(false);
            await loadDrafts();
          }, t("CV draft ready. Review the suggestions below."));
        }}
      >
        <fieldset disabled={task.busy}>
          <Field label={t("CV document (PDF or Word .docx)")}>
            <input
              type="file"
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              required
              onChange={(event) => {
                setFile(event.target.files?.[0] ?? null);
                setConsent(false);
              }}
            />
          </Field>
          <p>
            {t(
              "Maximum 4 MiB and 20 PDF pages. Use a document with selectable text; scanned PDFs need OCR first. Convert older .doc files to .docx.",
            )}
          </p>
          <label className="check">
            <input
              type="checkbox"
              required
              checked={consent}
              onChange={(event) => setConsent(event.target.checked)}
            />
            {t(
              "I agree to send the extracted CV text, which may contain personal information, to OpenAI for this extraction.",
            )}
          </label>
          <button className="primary">
            {task.busy ? t("Extracting CV\u2026") : t("Extract CV with AI")}
          </button>
        </fieldset>
      </form>
      {loadError && (
        <p role="alert">
          {t("Saved drafts could not be loaded.")}{" "}
          <button
            onClick={() => {
              void task.run(loadDrafts, t("Drafts loaded."));
            }}
          >
            {t("Retry loading drafts")}
          </button>
        </p>
      )}
      {!!savedDrafts.length && (
        <Field label={t("Resume a saved CV draft")}>
          <select
            value={draft?.id ?? ""}
            disabled={task.busy}
            onChange={(event) => {
              setDraft(
                savedDrafts.find((item) => item.id === event.target.value) ??
                  null,
              );
              setReviewed(false);
            }}
          >
            <option value="">{t("Choose a draft")}</option>
            {savedDrafts.map((item) => (
              <option key={item.id} value={item.id}>
                {item.filename}
              </option>
            ))}
          </select>
        </Field>
      )}
      {task.feedback}
      {draft && (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void task.run(async () => {
              if (!reviewed || !allowed.length)
                throw new Error(
                  t(
                    "Confirm the reviewed facts and choose at least one permitted use.",
                  ),
                );
              const saved = await saveDraft();
              await api(`/candidate/cv/drafts/${saved.id}/apply`, "POST", {
                expected_version: saved.version,
                expected_profile_version: profile.version,
                review_confirmed: true,
                allowed_uses: allowed,
              });
              setDraft(null);
              setReviewed(false);
              await loadDrafts();
              await refresh();
            }, t("Profile and evidence updated. Review your profile and publish its version when ready."));
          }}
        >
          <fieldset disabled={task.busy}>
            <h3>{t("Review your CV draft")}</h3>
            <p>
              {t(
                "AI extraction is a suggestion, not independent verification. Check names, dates, qualifications and every claim against the source.",
              )}
            </p>
            {draft.warnings.map((warning, index) => (
              <p key={index} role="note">
                {warning}
              </p>
            ))}
            <Field label={t("Display name")}>
              <input
                value={draft.display_name ?? ""}
                maxLength={200}
                onChange={(event) =>
                  change({ display_name: event.target.value || null })
                }
              />
            </Field>
            <Field label={t("Target roles (comma-separated)")}>
              <input
                value={draft.target_roles.join(", ")}
                onChange={(event) =>
                  change({
                    target_roles: event.target.value
                      .split(",")
                      .map((value) => value.trim()),
                  })
                }
                onBlur={() =>
                  change({ target_roles: draft.target_roles.filter(Boolean) })
                }
              />
            </Field>
            <Field label={t("Locations (comma-separated)")}>
              <input
                value={draft.locations.join(", ")}
                onChange={(event) =>
                  change({
                    locations: event.target.value
                      .split(",")
                      .map((value) => value.trim()),
                  })
                }
                onBlur={() =>
                  change({ locations: draft.locations.filter(Boolean) })
                }
              />
            </Field>
            <p>
              {t(
                "Search markets and working arrangements retain your existing profile settings. You can adjust them in the profile form below.",
              )}
            </p>
            <details>
              <summary>{t("View extracted source text")}</summary>
              <pre className="raw-text">{draft.source_text}</pre>
            </details>
            {draft.facts.map((fact, index) => (
              <section className="draft-fact" key={index}>
                <Field label={t("Claim {0}", [index + 1])}>
                  <textarea
                    required
                    maxLength={3000}
                    value={fact.claim}
                    onChange={(event) =>
                      change({
                        facts: draft.facts.map((item, i) =>
                          i === index
                            ? { ...item, claim: event.target.value }
                            : item,
                        ),
                      })
                    }
                  />
                </Field>
                <Field label={t("Category {0}", [index + 1])}>
                  <select
                    value={fact.category}
                    onChange={(event) =>
                      change({
                        facts: draft.facts.map((item, i) =>
                          i === index
                            ? {
                                ...item,
                                category: event.target
                                  .value as DraftFact["category"],
                              }
                            : item,
                        ),
                      })
                    }
                  >
                    {categories.map((category) => (
                      <option key={category} value={category}>
                        {t(
                          category.charAt(0).toUpperCase() + category.slice(1),
                        )}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label={t("Source excerpt {0}", [index + 1])}>
                  <textarea
                    value={fact.quote}
                    maxLength={3000}
                    onChange={(event) =>
                      change({
                        facts: draft.facts.map((item, i) =>
                          i === index
                            ? { ...item, quote: event.target.value }
                            : item,
                        ),
                      })
                    }
                  />
                </Field>
                <p>
                  {t(
                    "Keep an exact excerpt from the CV. Leave it blank only for a new statement you are declaring yourself.",
                  )}
                </p>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={fact.sensitivity === "sensitive"}
                    onChange={(event) =>
                      change({
                        facts: draft.facts.map((item, i) =>
                          i === index
                            ? {
                                ...item,
                                sensitivity: event.target.checked
                                  ? "sensitive"
                                  : "private",
                              }
                            : item,
                        ),
                      })
                    }
                  />
                  {t("Sensitive fact \u2014 exclude from automatic selection")}
                </label>
                <button
                  type="button"
                  onClick={() =>
                    change({ facts: draft.facts.filter((_, i) => i !== index) })
                  }
                >
                  {t("Remove claim")}
                </button>
              </section>
            ))}
            <button
              type="button"
              disabled={draft.facts.length >= 80}
              onClick={() =>
                change({
                  facts: [
                    ...draft.facts,
                    {
                      claim: "",
                      category: "skill",
                      quote: "",
                      sensitivity: "private",
                    },
                  ],
                })
              }
            >
              {t("Add a claim")}
            </button>
            <button
              type="button"
              onClick={() => {
                void task.run(async () => {
                  await saveDraft();
                  await loadDrafts();
                }, t("Draft saved. Your profile has not changed."));
              }}
            >
              {t("Save draft for later")}
            </button>
            <fieldset>
              <legend>{t("Permitted uses for the reviewed facts")}</legend>
              {uses.map((use) => (
                <label className="check" key={use}>
                  <input
                    type="checkbox"
                    checked={allowed.includes(use)}
                    onChange={(event) => {
                      setAllowed(
                        event.target.checked
                          ? [...allowed, use]
                          : allowed.filter((item) => item !== use),
                      );
                      setReviewed(false);
                    }}
                  />
                  {
                    {
                      matching: "Matching",
                      cv: "CV",
                      cover_letter: t("Cover letter"),
                      application_form: t("Application forms"),
                    }[use]
                  }
                </label>
              ))}
            </fieldset>
            <label className="check">
              <input
                type="checkbox"
                required
                checked={reviewed}
                onChange={(event) => setReviewed(event.target.checked)}
              />
              {t(
                "I have reviewed the profile, claims and evidence, confirm they are accurate and authorise the selected uses.",
              )}
            </label>
            <button className="primary">
              {task.busy
                ? t("Saving\u2026")
                : t("Apply reviewed profile and evidence")}
            </button>
          </fieldset>
        </form>
      )}
    </section>
  );
}

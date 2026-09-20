import { t } from "./i18n";
import { useTask } from "./useTask";
import { lines, optional, value } from "./forms";
import { useState } from "react";
import { api } from "./api";
import type { Evidence, Fact, Profile } from "./types";
import { Field } from "./ui";
import CvImport from "./CvImport";
type Props = {
  profile: Profile;
  facts: Fact[];
  evidence: Evidence[];
  refresh: () => Promise<void>;
};
export default function ProfilePage({
  profile,
  facts,
  evidence,
  refresh,
}: Props) {
  const task = useTask();
  const [editingFact, setEditingFact] = useState<Fact | null>(null);
  const [editingEvidence, setEditingEvidence] = useState<Evidence | null>(null);
  const [draftActive, setDraftActive] = useState(false);
  const [tab, setTab] = useState<"profile" | "facts" | "evidence">("profile");
  const [dirtyProfileVersion, setDirtyProfileVersion] = useState<number | null>(
    null,
  );
  const profileDirty = dirtyProfileVersion === profile.version;
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">{t("YOUR STORY, YOUR NEXT STEP")}</p>
          <h1>{t("My profile")}</h1>
          <p>
            {t(
              "Start with your CV. We will help turn your experience into a profile you can trust.",
            )}
          </p>
        </div>
        <span className="tag">
          {t("Version ")}
          {profile.version} ·{" "}
          {profile.status === "reviewed" ? t("Reviewed") : t("Review pending")}
        </span>
      </div>
      <nav className="tabs" aria-label={t("Profile sections")}>
        <button
          aria-pressed={tab === "profile"}
          onClick={() => setTab("profile")}
        >
          {t("Profile")}
        </button>
        <details className="profile-tools">
          <summary>{t("Manage facts and sources")}</summary>
          <div className="actions">
            {(["facts", "evidence"] as const).map((key) => (
              <button
                key={key}
                aria-pressed={tab === key}
                onClick={() => setTab(key)}
              >
                {
                  {
                    profile: t("Profile"),
                    facts: t("Facts ({0})", [facts.length]),
                    evidence: t("Evidence ({0})", [evidence.length]),
                  }[key]
                }
              </button>
            ))}
          </div>
        </details>
      </nav>
      {task.feedback}
      <div hidden={tab !== "profile"}>
        <CvImport
          profile={profile}
          refresh={refresh}
          onDraftChange={setDraftActive}
        />
      </div>
      {
        <section
          className="panel narrow"
          hidden={tab !== "profile" || draftActive}
        >
          <h2>{t("Search direction")}</h2>
          <p className="muted">
            {t(
              "Tell us what you would like to do next. You can change these preferences at any time.",
            )}
          </p>
          {!!profile.target_roles.length && (
            <p>{profile.target_roles.join(" · ")}</p>
          )}
          <details className="profile-preferences">
            <summary>{t("Edit details and preferences")}</summary>
            <form
              key={profile.version}
              onChange={() => setDirtyProfileVersion(profile.version)}
              onSubmit={(event) => {
                event.preventDefault();
                const data = new FormData(event.currentTarget);
                void task.run(async () => {
                  await api("/candidate/profile", "PATCH", {
                    expected_version: profile.version,
                    display_name: optional(data, "display_name"),
                    target_roles: lines(data, "target_roles"),
                    locations: lines(data, "locations"),
                    markets: data.getAll("markets"),
                    work_modes: data.getAll("work_modes"),
                  });
                  await refresh();
                  setDirtyProfileVersion(null);
                });
              }}
            >
              <Field label={t("Display name")}>
                <input
                  name="display_name"
                  defaultValue={profile.display_name ?? ""}
                  maxLength={200}
                />
              </Field>
              <Field label={t("Desired roles (comma-separated)")}>
                <input
                  name="target_roles"
                  defaultValue={profile.target_roles.join(", ")}
                />
              </Field>
              <Field label={t("Locations (comma-separated)")}>
                <input
                  name="locations"
                  defaultValue={profile.locations.join(", ")}
                />
              </Field>
              <fieldset>
                <legend>{t("Markets")}</legend>
                {["IE", "GB"].map((market) => (
                  <label className="check" key={market}>
                    <input
                      type="checkbox"
                      name="markets"
                      value={market}
                      defaultChecked={profile.markets.includes(market)}
                    />
                    {market === "IE" ? t("Ireland") : t("United Kingdom")}
                  </label>
                ))}
              </fieldset>
              <fieldset>
                <legend>{t("Working arrangements")}</legend>
                {["hybrid", "remote", "onsite"].map((mode) => (
                  <label className="check" key={mode}>
                    <input
                      type="checkbox"
                      name="work_modes"
                      value={mode}
                      defaultChecked={profile.work_modes.includes(mode)}
                    />
                    {
                      {
                        hybrid: t("Hybrid"),
                        remote: t("Remote"),
                        onsite: t("On-site"),
                      }[mode]
                    }
                  </label>
                ))}
              </fieldset>
              <button className="primary" disabled={task.busy}>
                {t("Save profile")}
              </button>
            </form>
          </details>
          <div className="review-callout">
            {profileDirty && (
              <p role="status">
                {t("Save your profile changes before publishing this version.")}
              </p>
            )}
            <p>
              {t(
                "Check your information and sources, then confirm your profile to start comparing vacancies.",
              )}
            </p>
            <button
              disabled={task.busy || profileDirty}
              onClick={() => {
                void task.run(async () => {
                  await api("/candidate/profile/review", "POST", {
                    expected_version: profile.version,
                  });
                  await refresh();
                }, t("Profile version reviewed and preserved."));
              }}
            >
              {t("Confirm my profile")}
            </button>
            {profile.status === "reviewed" && (
              <a className="button primary" href="#inbox">
                {t("Explore opportunities")} →
              </a>
            )}
          </div>
        </section>
      }
      {tab === "evidence" && (
        <div className="split">
          <section className="panel">
            <h2>{editingEvidence ? t("Edit evidence") : t("New evidence")}</h2>
            <form
              key={editingEvidence?.id ?? "new"}
              onSubmit={(event) => {
                event.preventDefault();
                const data = new FormData(event.currentTarget);
                void task.run(async () => {
                  await api(
                    `/candidate/evidence${editingEvidence ? "/" + editingEvidence.id : ""}`,
                    editingEvidence ? "PATCH" : "POST",
                    {
                      ...(editingEvidence
                        ? { expected_version: editingEvidence.version }
                        : {}),
                      source_type: value(data, "source_type"),
                      source_ref: value(data, "source_ref"),
                      locator: value(data, "locator"),
                      content: value(data, "content"),
                      sensitivity: value(data, "sensitivity"),
                      review_confirmed: data.has("review_confirmed"),
                    },
                  );
                  setEditingEvidence(null);
                  await refresh();
                });
              }}
            >
              <Field label={t("Source type")}>
                <select
                  name="source_type"
                  defaultValue={
                    editingEvidence?.source_type ?? "candidate_attestation"
                  }
                >
                  {Object.entries({
                    candidate_attestation: t("Candidate statement"),
                    cv: "CV",
                    repository: t("Repository"),
                    certificate: t("Certificate"),
                    employment_record: t("Professional record"),
                    other: t("Other"),
                  }).map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label={t("Source reference")}>
                <input
                  name="source_ref"
                  required
                  defaultValue={editingEvidence?.source_ref}
                  placeholder={t("URL or document ID")}
                />
              </Field>
              <Field label={t("Locator")}>
                <input
                  name="locator"
                  required
                  defaultValue={editingEvidence?.locator}
                  placeholder={t("Page, section or file")}
                />
              </Field>
              <Field label={t("Excerpt or statement")}>
                <textarea
                  name="content"
                  required
                  rows={5}
                  maxLength={10000}
                  defaultValue={editingEvidence?.content}
                />
              </Field>
              <Sensitivity current={editingEvidence?.sensitivity} />
              <label className="check">
                <input type="checkbox" name="review_confirmed" />
                {t("I reviewed the source and the recorded excerpt.")}
              </label>
              <button className="primary" disabled={task.busy}>
                {t("Save evidence")}
              </button>
              {editingEvidence && (
                <button type="button" onClick={() => setEditingEvidence(null)}>
                  {t("Cancel editing")}
                </button>
              )}
            </form>
          </section>
          <section className="panel">
            <h2>{t("Recorded evidence")}</h2>
            {!evidence.length && (
              <p>{t("Start by recording the source that supports a fact.")}</p>
            )}
            {evidence.map((item) => (
              <article
                className="record"
                key={item.id}
                id={`evidence-${item.id}`}
              >
                <h3>{item.source_ref}</h3>
                <p>
                  {item.locator} ·{" "}
                  {item.reviewed_at ? t("Reviewed") : t("Pending")}
                </p>
                <details>
                  <summary>{t("View content and reference")}</summary>
                  <p className="preserve">{item.content}</p>
                  <p className="muted">
                    {t("Snippet hash: ")}
                    {item.content_sha256}
                  </p>
                </details>
                <div className="actions">
                  <button onClick={() => setEditingEvidence(item)}>
                    {t("Edit evidence")}
                  </button>
                  <button
                    onClick={() => {
                      void task.run(async () => {
                        await api(
                          `/candidate/evidence/${item.id}?expected_version=${item.version}`,
                          "DELETE",
                        );
                        await refresh();
                      });
                    }}
                  >
                    {t("Remove evidence")}
                  </button>
                </div>
              </article>
            ))}
          </section>
        </div>
      )}
      {tab === "facts" && (
        <div className="split">
          <section className="panel">
            <h2>{editingFact ? t("Edit fact") : t("New fact")}</h2>
            <form
              key={editingFact?.id ?? "new"}
              onSubmit={(event) => {
                event.preventDefault();
                const data = new FormData(event.currentTarget);
                void task.run(async () => {
                  await api(
                    `/candidate/facts${editingFact ? "/" + editingFact.id : ""}`,
                    editingFact ? "PATCH" : "POST",
                    {
                      ...(editingFact
                        ? { expected_version: editingFact.version }
                        : {}),
                      claim: value(data, "claim"),
                      category: value(data, "category"),
                      status: value(data, "status"),
                      sensitivity: value(data, "sensitivity"),
                      evidence_ids: data.getAll("evidence_ids"),
                      allowed_uses: data.getAll("allowed_uses"),
                      valid_from: optional(data, "valid_from")
                        ? new Date(value(data, "valid_from")).toISOString()
                        : null,
                      valid_until: optional(data, "valid_until")
                        ? new Date(value(data, "valid_until")).toISOString()
                        : null,
                      review_confirmed: data.has("review_confirmed"),
                    },
                  );
                  setEditingFact(null);
                  await refresh();
                });
              }}
            >
              <Field label={t("Factual statement")}>
                <textarea
                  required
                  name="claim"
                  rows={4}
                  maxLength={3000}
                  defaultValue={editingFact?.claim}
                />
              </Field>
              <Field label={t("Category")}>
                <select
                  name="category"
                  defaultValue={editingFact?.category ?? "skill"}
                >
                  {Object.entries({
                    skill: t("Skill"),
                    experience: t("Experience"),
                    education: t("Education"),
                    project: t("Project"),
                    certification: t("Certification"),
                    achievement: t("Achievement"),
                    preference: t("Preference"),
                    constraint: t("Restriction"),
                  }).map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label={t("Fact status")}>
                <select
                  name="status"
                  defaultValue={editingFact?.status ?? "unverified"}
                >
                  <option value="unverified">{t("Not verified")}</option>
                  <option value="verified">{t("Verified")}</option>
                  <option value="expired">{t("Expired")}</option>
                  <option value="revoked">{t("Revoked")}</option>
                </select>
              </Field>
              <fieldset>
                <legend>{t("Supporting evidence")}</legend>
                {!evidence.length && <p>{t("Record evidence first.")}</p>}
                {evidence.map((item) => (
                  <label className="check" key={item.id}>
                    <input
                      name="evidence_ids"
                      type="checkbox"
                      value={item.id}
                      defaultChecked={editingFact?.evidence_ids.includes(
                        item.id,
                      )}
                    />
                    {item.source_ref} ·{" "}
                    {item.reviewed_at ? t("Reviewed") : t("Pending")}
                  </label>
                ))}
              </fieldset>
              <fieldset>
                <legend>{t("Allowed uses")}</legend>
                {Object.entries({
                  matching: "Matching",
                  cv: "CV",
                  cover_letter: t("Letter"),
                  application_form: t("Form"),
                }).map(([key, label]) => (
                  <label className="check" key={key}>
                    <input
                      name="allowed_uses"
                      type="checkbox"
                      value={key}
                      defaultChecked={editingFact?.allowed_uses.includes(key)}
                    />
                    {label}
                  </label>
                ))}
              </fieldset>
              <div className="form-grid">
                <Field label={t("Valid from (UTC)")}>
                  <input
                    type="date"
                    name="valid_from"
                    defaultValue={editingFact?.valid_from?.slice(0, 10)}
                  />
                </Field>
                <Field label={t("Valid until (UTC, exclusive)")}>
                  <input
                    type="date"
                    name="valid_until"
                    defaultValue={editingFact?.valid_until?.slice(0, 10)}
                  />
                </Field>
              </div>
              <Sensitivity current={editingFact?.sensitivity} />
              <label className="check">
                <input type="checkbox" name="review_confirmed" />
                {t("I confirm the review of this fact and its evidence.")}
              </label>
              <button className="primary" disabled={task.busy}>
                {t("Save fact")}
              </button>
              {editingFact && (
                <button type="button" onClick={() => setEditingFact(null)}>
                  {t("Cancel editing")}
                </button>
              )}
            </form>
          </section>
          <section className="panel">
            <h2>{t("Recorded facts")}</h2>
            {!facts.length && <p>{t("No facts recorded.")}</p>}
            {facts.map((item) => (
              <article className="record" key={item.id}>
                <h3>{item.claim}</h3>
                <p>
                  {item.status} ·{" "}
                  {item.allowed_uses.join(", ") || t("No authorised uses")}
                </p>
                <p>
                  {item.evidence_ids.length}
                  {t(" evidence(s)")}
                </p>
                <div className="actions">
                  <button onClick={() => setEditingFact(item)}>
                    {t("Edit fact")}
                  </button>
                  <button
                    onClick={() => {
                      void task.run(async () => {
                        await api(
                          `/candidate/facts/${item.id}?expected_version=${item.version}`,
                          "DELETE",
                        );
                        await refresh();
                      });
                    }}
                  >
                    {t("Remove fact")}
                  </button>
                </div>
              </article>
            ))}
          </section>
        </div>
      )}
    </>
  );
}
function Sensitivity({ current }: { current?: string }) {
  return (
    <Field label={t("Sensitivity")}>
      <select name="sensitivity" defaultValue={current ?? "private"}>
        <option value="public">{t("Public")}</option>
        <option value="private">{t("Private")}</option>
        <option value="sensitive">{t("Sensitive")}</option>
      </select>
    </Field>
  );
}

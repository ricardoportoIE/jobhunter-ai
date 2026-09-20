import { localisedLabels } from "./i18n";
export type Entity = {
  id: string;
  version: number;
};
export type Profile = Entity & {
  display_name: string | null;
  status: "draft" | "reviewed";
  target_roles: string[];
  markets: string[];
  locations: string[];
  work_modes: string[];
};
export type Evidence = Entity & {
  source_type: string;
  source_ref: string;
  locator: string;
  content: string;
  content_sha256: string;
  sensitivity: string;
  reviewed_at: string | null;
};
export type Fact = Entity & {
  claim: string;
  category: string;
  status: string;
  evidence_ids: string[];
  sensitivity: string;
  allowed_uses: string[];
  valid_from: string | null;
  valid_until: string | null;
};
export const categories = localisedLabels({
  technical_skills: "Technical skills",
  seniority_experience: "Experience",
  portfolio: "Portfolio",
  education: "Education",
  location_work_mode: "Location and working arrangement",
  salary: "Salary",
  work_authorisation_hours: "Authorisation and hours",
  career_value: "Career strategy",
});
export type Category = keyof typeof categories;
export type Requirement = {
  id: string;
  text: string;
  category: Category;
  importance: "required" | "preferred";
  is_eliminatory: boolean;
  source_locator: string;
  future_authorisation: boolean;
};
export type Job = Entity & {
  source_update_pending?: boolean;
  title: string | null;
  company_name: string | null;
  location: string | null;
  country: string | null;
  work_mode: string | null;
  employment_type: string | null;
  seniority: string | null;
  salary: {
    minimum: number | null;
    maximum: number | null;
    currency: string | null;
    period: string | null;
  } | null;
  work_authorisation: string | null;
  sponsorship: string | null;
  requirements: Requirement[];
  risk_flags: string[];
  status: string;
  archived: boolean;
  raw_text: string;
  source_url: string | null;
  source_name: string;
  content_sha256: string;
};
export type Assessment = {
  requirement_id: string;
  status: string;
  reason: string;
  fact_ids: string[];
};
export type Match = Entity & {
  clarifications?: import("./Clarifications").Clarification[];
  clarification_resolutions?: import("./Clarifications").Resolution[];
  job_id: string;
  score: number | null;
  coverage: number;
  recommendation: string;
  employment_gate: string;
  stale: boolean;
  review_flags: string[];
  gaps: {
    requirement_id: string;
    text: string;
    status: string;
    reason: string;
  }[];
  blockers: {
    requirement_id: string | null;
    reason: string;
  }[];
  breakdown: {
    category: Category;
    weight: number;
    coverage: number;
    attainment: number | null;
    assessments: (Assessment & {
      evidence_ids: string[];
    })[];
  }[];
  created_at: string;
  profile_snapshot: {
    facts: Fact[];
    evidence: Evidence[];
  };
};
export const recommendations: Record<string, string> = localisedLabels({
  PRIORITISE: "Prioritise",
  APPLY_AFTER_REVIEW: "Apply after review",
  REVIEW: "Review",
  TRACK_OR_ARCHIVE: "Follow up or archive",
  BLOCKED: "Blocked",
});
export const gates: Record<string, string> = localisedLabels({
  READY_WITHIN_CONFIRMED_LIMITS: "Within confirmed limits",
  REVIEW_BEFORE_START: "Review before starting work",
  BLOCKED: "Confirmed incompatibility",
});
export const outcomes: Record<string, string> = localisedLabels({
  unknown: "Unknown",
  met: "Met",
  partial: "Partial",
  unmet: "Not met",
});
export const reviewFlags: Record<string, string> = localisedLabels({
  CLARIFICATION_REQUIRED: "Clarification needed before prioritising",
  SPONSORSHIP_UNKNOWN: "Sponsorship not declared",
  FACT_NOT_ELIGIBLE:
    "There are facts without validity or authorisation for this analysis",
  SENIORITY_EXCLUDED: "Vacancy level outside confirmed target",
});

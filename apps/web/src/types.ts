export type Entity = { id: string; version: number };
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
export const categories = {
  technical_skills: "Competências técnicas",
  seniority_experience: "Experiência",
  portfolio: "Portfólio",
  education: "Formação",
  location_work_mode: "Local e modalidade",
  salary: "Salário",
  work_authorisation_hours: "Autorização e horário",
  career_value: "Estratégia de carreira",
};
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
  blockers: { requirement_id: string | null; reason: string }[];
  breakdown: {
    category: Category;
    weight: number;
    coverage: number;
    attainment: number | null;
    assessments: (Assessment & { evidence_ids: string[] })[];
  }[];
  created_at: string;
  profile_snapshot: { facts: Fact[]; evidence: Evidence[] };
};
export const recommendations: Record<string, string> = {
  PRIORITISE: "Priorizar",
  APPLY_AFTER_REVIEW: "Candidatar após revisão",
  REVIEW: "Revisar",
  TRACK_OR_ARCHIVE: "Acompanhar ou arquivar",
  BLOCKED: "Bloqueada",
};
export const gates: Record<string, string> = {
  READY_WITHIN_CONFIRMED_LIMITS: "Dentro dos limites confirmados",
  REVIEW_BEFORE_START: "Revisar antes de iniciar trabalho",
  BLOCKED: "Incompatibilidade confirmada",
};
export const outcomes: Record<string, string> = {
  unknown: "Desconhecido",
  met: "Atendido",
  partial: "Parcial",
  unmet: "Não atendido",
};

export const reviewFlags: Record<string, string> = {
  SPONSORSHIP_UNKNOWN: "Sponsorship não informado",
  FACT_NOT_ELIGIBLE: "Há fatos sem validade ou autorização para esta análise",
  SENIORITY_EXCLUDED: "Nível da vaga fora do alvo confirmado",
};

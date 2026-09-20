import type { Entity } from "./types";

export type DiscoverySource = Entity & {
  provider: "greenhouse" | "gmail";
  name: string;
  reference: string;
  enabled: boolean;
  ready: boolean;
  connected: boolean;
  terms_url: string;
  permission_note: string;
  review_until: string | null;
  label_id: string;
  label_name: string;
  last_synced_at: string | null;
  next_sync_at: string | null;
  last_error: string | null;
  active_run: string | null;
};
export type DiscoveryItem = Entity & {
  title: string;
  company: string | null;
  location: string | null;
  url: string;
  raw_text: string;
  item_type: "vacancy" | "email";
  source_id: string;
  links: string[];
  availability: "listed" | "not_listed";
  notice: "new" | "changed" | "missing";
  seen: boolean;
  dismissed: boolean;
  job_id: string | null;
  update_pending?: boolean;
  last_seen_at: string;
};
export type DiscoveryRun = Entity & {
  status: string;
  started_at: string;
  finished_at: string | null;
  counts: Record<string, number>;
  error_code: string | null;
};

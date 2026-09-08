// frontend/src/types/scheme.ts
//
// Types for the required-documents / application-timeline / evidence-based
// reasoning fields the backend now attaches to eligible scheme recommendations
// (see docs/SCHEME_REQUIREMENTS_FEATURE_PLAN.md sections 5.1, 5.2, 5.6, 8a).
//
// These narrowly type only the NEW fields -- the rest of the recommendation
// object (scheme_id, scheme_name, success_probability, explanation, etc.) is
// still consumed as `any` elsewhere in Dashboard.tsx, unchanged.

export type DocumentRequirement = "mandatory" | "conditional" | "unknown";
export type MatchConfidence = "high" | "low" | "none";

export interface RequiredDocumentItem {
  raw_text: string;
  display_name: string;
  doc_type: string;
  requirement: DocumentRequirement;
  condition_text: string | null;
  match_confidence: MatchConfidence;
  links: string[];
}

export type RequiredDocumentsStatus =
  | "available"
  | "unavailable"
  | "fetch_failed"
  | "not_fetched";

export interface RequiredDocuments {
  status: RequiredDocumentsStatus;
  source?: string | null;
  source_url?: string | null;
  fetched_at?: string | null;
  raw_markdown?: string | null;
  items: RequiredDocumentItem[];
  item_count: number;
  unmatched_count: number;
  extractor_version: number;
}

export interface ApplicationMode {
  mode: string;
  url: string | null;
}

export interface TimelineMention {
  kind: string;
  excerpt: string;
  field?: string | null;
}

export type ApplicationTimelineStatus = "window" | "open_ended" | "unknown";

export interface ApplicationTimeline {
  status: ApplicationTimelineStatus;
  open_date?: string | null;
  close_date?: string | null;
  open_date_raw?: string | null;
  close_date_raw?: string | null;
  open_date_source?: string | null;
  close_date_source?: string | null;
  application_modes: ApplicationMode[];
  text_mentions: TimelineMention[];
  fetched_at?: string | null;
  extractor_version: number;
}

export type TimelineStateKind =
  | "open"
  | "closing_soon"
  | "expired"
  | "open_ended"
  | "unknown"
  | "unknown_with_mention";

export interface TimelineState {
  state: TimelineStateKind;
  days_remaining: number | null;
  label: string;
}

export interface MatchSignal {
  signal_type: string;
  field: string;
  operator: string;
  scheme_value: unknown;
  profile_value: unknown;
  profile_field?: string | null;
  text: string;
  evidence_source: string;
  rule_provenance: string;
}

export type ReasonConfidence = "verified" | "high" | "medium" | "low";

export type Confidence = "high" | "medium" | "low";
export type BBox = [number, number, number, number];
export type Severity = "high" | "medium" | "low" | "info";

export interface ExtractedField {
  key: string;
  label: string;
  value: string;
  confidence: Confidence;
  source: string;
  bbox: BBox;
  type: string; // text | number | date | currency | email | id
  group: string;
}

export interface TableRow {
  cells: Record<string, string>;
  bbox: BBox;
  confidence: Confidence;
}

export interface ExtractedTable {
  name: string;
  label: string;
  columns: string[];
  rows: TableRow[];
}

export interface Extraction {
  domain: string;
  fields: ExtractedField[];
  tables: ExtractedTable[];
  additional_fields: ExtractedField[];
  overall_confidence: Confidence;
}

export interface Check {
  rule: string;
  passed: boolean;
  reason: string;
}
export interface ValidationResult {
  passed: boolean;
  checks: Check[];
}

export interface Flag {
  check: string;
  severity: Severity;
  reason: string;
}
export interface IntegrityResult {
  passed: boolean;
  flags: Flag[];
}

export interface SimilarityResult {
  score: number;
  label: string;
  verdict: string;
  detail: string;
}

export interface DomainInfo {
  name: string;
  label: string;
  description: string;
  icon: string;
  needs_second_input: boolean;
  second_input_label: string;
  integrity_label: string;
}

export interface ProcessResponse {
  domain: string;
  domain_label: string;
  integrity_label: string;
  extraction: Extraction;
  validation: ValidationResult;
  integrity: IntegrityResult;
  similarity: SimilarityResult | null;
  model_used: string;
  escalated: boolean;
  page_image_b64: string;
  source_type: string;
}

export interface ApproveResponse {
  ledger_id: number;
  mock_action: { status: string; action: string; message: string };
  csv_row: string;
}

export interface Stats {
  processed: number;
  approved: number;
  flagged: number;
  escalated: number;
  escalation_rate: number;
  confidence_distribution: { high: number; medium: number; low: number };
  by_domain: Record<string, number>;
}

export interface ActivityItem {
  id: number;
  ts: string;
  type: "processed" | "approved" | "flagged" | "escalated";
  domain: string;
  ref: string;
  party: string;
  summary: string;
  severity: "high" | "medium" | "low" | "info" | "ok";
  meta: Record<string, unknown>;
}

export interface LedgerRecord {
  id: number;
  domain: string;
  ref: string;
  party: string;
  account: string;
  identity: string;
  amount: number | null;
  doc_date: string;
  fields: Record<string, string>;
  approved_at: string;
  mock_action: string;
}

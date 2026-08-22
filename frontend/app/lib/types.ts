export type Confidence = "high" | "medium" | "low";
export type BBox = [number, number, number, number];

export interface FieldValue {
  value: string;
  confidence: Confidence;
  source: string;
  bbox: BBox;
}

export interface LineItem {
  description: string;
  quantity: number;
  unit_price: number;
  amount: number;
  confidence: Confidence;
  bbox: BBox;
}

export interface Extraction {
  invoice_number: FieldValue;
  invoice_date: FieldValue;
  vendor_name: FieldValue;
  vendor_bank_account: FieldValue;
  currency: FieldValue;
  line_items: LineItem[];
  subtotal: FieldValue;
  tax: FieldValue;
  total: FieldValue;
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

export type Severity = "high" | "medium" | "low" | "info";

export interface Flag {
  check: string;
  severity: Severity;
  reason: string;
}

export interface FraudResult {
  passed: boolean;
  flags: Flag[];
}

export interface ProcessResponse {
  extraction: Extraction;
  validation: ValidationResult;
  fraud: FraudResult;
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
}

export interface ActivityItem {
  id: number;
  ts: string;
  type: "processed" | "approved" | "flagged" | "escalated";
  invoice_number: string;
  vendor_name: string;
  summary: string;
  severity: "high" | "medium" | "low" | "info" | "ok";
  meta: Record<string, unknown>;
}

export interface LedgerRow {
  id: number;
  invoice_number: string;
  vendor_name: string;
  vendor_bank_account: string;
  invoice_date: string;
  currency: string;
  subtotal: number | null;
  tax: number | null;
  total: number | null;
  approved_at: string;
  mock_action: string;
  line_items: LineItem[];
}

// The scalar field keys the DocViewer/FieldReview cross-highlight on.
export type ScalarKey =
  | "invoice_number"
  | "invoice_date"
  | "vendor_name"
  | "vendor_bank_account"
  | "currency"
  | "subtotal"
  | "tax"
  | "total";

export const SCALAR_KEYS: ScalarKey[] = [
  "invoice_number",
  "invoice_date",
  "vendor_name",
  "vendor_bank_account",
  "currency",
  "subtotal",
  "tax",
  "total",
];

export const FIELD_LABELS: Record<ScalarKey, string> = {
  invoice_number: "Invoice Number",
  invoice_date: "Invoice Date",
  vendor_name: "Vendor",
  vendor_bank_account: "Bank Account",
  currency: "Currency",
  subtotal: "Subtotal",
  tax: "Tax",
  total: "Total",
};

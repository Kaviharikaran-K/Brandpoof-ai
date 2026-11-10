export type Role = "admin" | "creator" | "reviewer";

export interface User {
  id: number;
  email: string;
  full_name: string;
}

export interface Membership {
  org_id: number;
  org_name: string;
  slug: string;
  role: Role;
}

export interface Me {
  user: User;
  memberships: Membership[];
}

export type FactStatus = "pending" | "approved";

export interface Fact {
  id: number;
  org_id: number;
  fact_id: string;
  name: string;
  approved_value: string;
  description: string;
  source_ref: string;
  version: number;
  effective_date: string | null;
  expiry_date: string | null;
  approval_status: FactStatus;
  confirmed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Term {
  id: number;
  org_id: number;
  rule_type: "required" | "prohibited";
  term: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface Guideline {
  id: number;
  org_id: number;
  title: string;
  file_name: string;
  content_type: string;
  size_bytes: number;
  uploaded_by_id: number | null;
  created_at: string;
}

export interface SourceDoc {
  id: number;
  org_id: number;
  title: string;
  file_name: string;
  content_type: string;
  size_bytes: number;
  uploaded_by_id: number | null;
  created_at: string;
}

export interface Asset {
  id: number;
  org_id: number;
  asset_type: "logo" | "colour" | string;
  name: string;
  colour_value: string | null;
  file_name: string | null;
  content_type: string | null;
  size_bytes: number | null;
  created_at: string;
}

export interface BrandProfile {
  id: number;
  org_id: number;
  name: string;
  product_name: string;
  tagline: string;
  tone: string;
  description: string;
  updated_at: string;
}

export interface Org {
  id: number;
  name: string;
  slug: string;
  role: Role;
  created_at: string;
}

export interface Member {
  user_id: number;
  email: string;
  full_name: string;
  role: Role;
  joined_at: string;
}

export interface AuditEntry {
  id: number;
  action: string;
  entity_type: string;
  entity_id: string | null;
  details: Record<string, unknown>;
  user_email: string | null;
  created_at: string;
}

export type SubmissionStatus =
  | "Draft"
  | "Submitted"
  | "Under Analysis"
  | "Changes Requested"
  | "Clarification Required"
  | "Resubmitted"
  | "Approved"
  | "Rejected";

export type Severity = "Critical" | "Major" | "Minor" | "Information";

export interface RelatedFactEvidence {
  fact_id?: string;
  name?: string;
  value?: string;
  source_ref?: string;
  version?: number;
  effective_date?: string;
  expiry_date?: string;
  approval_status?: string;
}

export interface FindingEvidence extends RelatedFactEvidence {
  related_facts?: RelatedFactEvidence[];
  claim?: { topic?: string; value?: string };
  rule?: string;
  rule_type?: string;
  term?: string;
  phrase?: string;
  engine?: string;
  count?: number;
  words?: number;
}

export interface Finding {
  id: number;
  finding_id: string;
  category: string;
  severity: Severity;
  detected_text: string;
  start_offset: number;
  end_offset: number;
  evidence: FindingEvidence | null;
  explanation: string;
  suggested_correction: string | null;
  confidence: string | null;
  review_status: string;
  requires_clarification: boolean;
  needs_human_review: boolean;
}

export interface VisualPaletteMatch {
  hex: string;
  share: number;
  nearest_hex: string;
  nearest_name: string;
  delta_e: number;
  verdict: "match" | "close" | "deviation" | string;
}

export interface VisualContrastPair {
  foreground: string;
  background: string;
  ratio: number;
  wcag_aa_normal: boolean;
  wcag_aa_large: boolean;
}

export interface VisualLogoResult {
  checked: boolean;
  matched: boolean | null;
  best_score: number | null;
  threshold?: number;
}

export interface VisualReport {
  available: boolean;
  capabilities: {
    pixel_analysis: boolean;
    ocr: boolean;
    logo_match: boolean;
    palette_configured: boolean;
    logo_configured: boolean;
  };
  limitations: string[];
  note: string;
  image: { width?: number; height?: number; format?: string };
  dominant_colours: { hex: string; share: number }[];
  palette_matches: VisualPaletteMatch[];
  contrast: VisualContrastPair[];
  logo: VisualLogoResult;
}

export interface AnalysisRun {
  id: number;
  submission_id: number;
  revision_id: number;
  engine: string;
  finding_count: number;
  created_at: string;
  visual_report: VisualReport | null;
  findings: Finding[];
}

export interface SubmissionRevision {
  id: number;
  submission_id: number;
  revision_number: number;
  content: string;
  created_by_id: number;
  created_at: string;
}

export interface ReviewComment {
  id: number;
  submission_id: number;
  author_email: string;
  author_name: string;
  body: string;
  created_at: string;
}

export interface ApprovalDecision {
  id: number;
  submission_id: number;
  decision: string;
  from_status: string;
  to_status: string;
  note: string;
  decided_by_email: string;
  decided_at: string;
}

export interface SubmissionSummary {
  id: number;
  title: string;
  submission_type: string;
  status: SubmissionStatus;
  created_by_id: number;
  created_by_email: string | null;
  current_revision_number: number | null;
  revision_count: number;
  latest_finding_count: number | null;
  latest_clarification_count: number | null;
  created_at: string;
  updated_at: string;
}

export interface SubmissionDetail {
  id: number;
  org_id: number;
  title: string;
  submission_type: string;
  status: SubmissionStatus;
  created_by_id: number;
  created_by_email: string | null;
  has_image: boolean;
  image_name: string | null;
  alt_text: string | null;
  created_at: string;
  updated_at: string;
  decided_at: string | null;
  revisions: SubmissionRevision[];
  runs: AnalysisRun[];
  comments: ReviewComment[];
  decisions: ApprovalDecision[];
}

export interface StatusCount {
  status: string;
  count: number;
}

export interface CategoryCount {
  category: string;
  count: number;
}

export interface SeverityCount {
  severity: string;
  count: number;
}

export interface RepeatedIssue {
  category: string;
  detected_text: string;
  count: number;
}

export interface AnalyticsTotals {
  submissions_total: number;
  submissions_approved: number;
  submissions_rejected: number;
  submissions_pending: number;
  submissions_draft: number;
  findings_total: number;
  findings_latest: number;
  clarification_findings: number;
  needs_human_review: number;
  decided_total: number;
  avg_review_hours: number | null;
  avg_revision_cycles: number | null;
}

export interface AnalyticsOverview {
  totals: AnalyticsTotals;
  status_counts: StatusCount[];
  categories: CategoryCount[];
  severities: SeverityCount[];
  top_issues: RepeatedIssue[];
  date_from: string | null;
  date_to: string | null;
}

export interface AnalyticsIssues {
  categories: CategoryCount[];
  severities: SeverityCount[];
  repeated_terminology: RepeatedIssue[];
  top_factual_mismatches: RepeatedIssue[];
  top_clarification_claims: RepeatedIssue[];
  needs_human_review: number;
  date_from: string | null;
  date_to: string | null;
}

export interface TrendPoint {
  date: string;
  submissions: number;
  findings: number;
  decisions: number;
}

export interface CategoryTrendPoint {
  date: string;
  category: string;
  count: number;
}

export interface AnalyticsTrends {
  series: TrendPoint[];
  by_category: CategoryTrendPoint[];
  date_from: string;
  date_to: string;
}

export interface AiConsent {
  consent: boolean;
  provider_configured: boolean;
  disclosure: string;
  note: string;
  updated_at: string;
}

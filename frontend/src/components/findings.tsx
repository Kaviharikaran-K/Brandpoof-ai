"use client";

import { ChevronRight } from "lucide-react";

import { cx } from "@/components/ui";
import type { Finding, FindingEvidence, Severity } from "@/lib/types";

const SEVERITY_STYLES: Record<string, string> = {
  Critical: "bg-red-wash text-red-brand border-red-brand/40",
  Major: "bg-amber-wash text-amber-brand border-amber-brand/40",
  Minor: "bg-teal-wash text-teal-dark border-teal/40",
  Information: "bg-paper text-ink-soft border-hairline",
};

const MARK_CLASSES: Record<string, string> = {
  Critical: "finding-critical",
  Major: "finding-major",
  Minor: "finding-minor",
  Information: "finding-info",
};

export function SeverityTag({ severity }: { severity: Severity | string }) {
  return (
    <span
      className={cx(
        "inline-flex items-center rounded border px-1.5 py-0.5 text-[11px] font-semibold",
        SEVERITY_STYLES[severity] ?? SEVERITY_STYLES.Information
      )}
    >
      {severity}
    </span>
  );
}

interface Range {
  start: number;
  end: number;
  finding: Finding;
}

function clipRanges(findings: Finding[], length: number): Range[] {
  const ranges = findings
    .filter((f) => f.end_offset > f.start_offset && f.start_offset < length)
    .map((f) => ({
      start: Math.max(0, f.start_offset),
      end: Math.min(length, f.end_offset),
      finding: f,
    }))
    .sort((a, b) => a.start - b.start || b.end - a.end);

  const clipped: Range[] = [];
  let cursor = 0;
  for (const range of ranges) {
    const start = Math.max(range.start, cursor);
    if (range.end <= start) continue;
    clipped.push({ start, end: range.end, finding: range.finding });
    cursor = range.end;
  }
  return clipped;
}

export function HighlightedText({
  content,
  findings,
  activeId,
}: {
  content: string;
  findings: Finding[];
  activeId?: number | null;
}) {
  const ranges = clipRanges(findings, content.length);
  const parts: React.ReactNode[] = [];
  let position = 0;

  ranges.forEach(({ start, end, finding }) => {
    if (start > position) parts.push(content.slice(position, start));
    const markClass = finding.requires_clarification
      ? "finding-clarification hatched"
      : MARK_CLASSES[finding.severity] ?? "finding-info";
    parts.push(
      <mark
        key={`${finding.id}-${start}`}
        className={cx(markClass, activeId === finding.id && "finding-active")}
        title={`${finding.severity}: ${finding.category}`}
      >
        {content.slice(start, end)}
      </mark>
    );
    position = end;
  });

  if (position < content.length) parts.push(content.slice(position));

  return <p className="whitespace-pre-wrap font-sans text-[14px] leading-relaxed text-ink">{parts}</p>;
}

function FactLine({ fact }: { fact: FindingEvidence }) {
  return (
    <div className="rounded border border-hairline bg-paper px-2 py-1.5">
      <p className="font-mono text-[11px] text-teal-dark">
        {fact.fact_id ?? "FACT"}
        {fact.name ? <span className="text-ink-soft"> · {fact.name}</span> : null}
      </p>
      {fact.value && <p className="mt-0.5 text-[12px] text-ink">Approved value: {fact.value}</p>}
      <p className="mt-0.5 text-[11px] text-ink-faint">
        {fact.source_ref ? `Source: ${fact.source_ref}` : "Source: not recorded"}
        {fact.version ? ` · v${fact.version}` : ""}
        {fact.approval_status ? ` · ${fact.approval_status}` : ""}
      </p>
      {(fact.effective_date || fact.expiry_date) && (
        <p className="text-[11px] text-ink-faint">
          {fact.effective_date ? `Effective ${fact.effective_date}` : "No effective date"}
          {fact.expiry_date ? ` · Expires ${fact.expiry_date}` : ""}
        </p>
      )}
    </div>
  );
}

export function EvidenceCitation({ evidence }: { evidence: FindingEvidence | null }) {
  if (!evidence) {
    return <p className="text-[11px] text-ink-faint">No evidence reference recorded.</p>;
  }

  const related = evidence.related_facts ?? [];
  const hasSingle = Boolean(evidence.fact_id);
  const hasRule = Boolean(evidence.rule || evidence.rule_type || evidence.phrase);

  return (
    <div className="space-y-1.5">
      {hasSingle && <FactLine fact={evidence} />}
      {related.length > 0 && (
        <div className="space-y-1.5">
          {related.map((fact, index) => (
            <FactLine key={`${fact.fact_id ?? "fact"}-${index}`} fact={fact} />
          ))}
        </div>
      )}
      {hasRule && (
        <p className="rounded border border-hairline bg-paper px-2 py-1.5 text-[11px] text-ink-soft">
          {evidence.rule ? `Rule: ${evidence.rule}` : null}
          {evidence.rule_type ? ` rule_type: ${evidence.rule_type}` : null}
          {evidence.term ? ` · term: ${evidence.term}` : null}
          {evidence.phrase ? ` · phrase: ${evidence.phrase}` : null}
          {evidence.engine ? ` · engine: ${evidence.engine}` : null}
        </p>
      )}
      {!hasSingle && related.length === 0 && !hasRule && (
        <p className="text-[11px] text-ink-faint">No linked approved fact for this finding.</p>
      )}
    </div>
  );
}

export function FindingCard({
  finding,
  active,
  onHover,
}: {
  finding: Finding;
  active: boolean;
  onHover: (id: number | null) => void;
}) {
  return (
    <div
      onMouseEnter={() => onHover(finding.id)}
      onMouseLeave={() => onHover(null)}
      onFocus={() => onHover(finding.id)}
      onBlur={() => onHover(null)}
      tabIndex={0}
      className={cx(
        "rounded border bg-white p-3 transition-colors",
        finding.requires_clarification ? "hatched border-red-brand/30" : "border-hairline",
        active && "border-ink"
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        <SeverityTag severity={finding.severity} />
        <span className="text-[12px] font-medium text-ink">{finding.category}</span>
        {finding.needs_human_review && (
          <span className="rounded border border-amber-brand/40 bg-amber-wash px-1.5 py-0.5 text-[10px] font-medium text-amber-brand">
            Requires human review
          </span>
        )}
        <span className="ml-auto font-mono text-[10px] text-ink-faint">{finding.finding_id}</span>
      </div>

      <p className="mt-2 text-[13px] text-ink">{finding.explanation}</p>

      {finding.detected_text && (
        <p className="mt-2 rounded border border-hairline bg-paper px-2 py-1 font-mono text-[11px] text-ink-soft">
          “{finding.detected_text}”
        </p>
      )}

      <div className="mt-2">
        <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-ink-faint">
          Evidence
        </p>
        <EvidenceCitation evidence={finding.evidence} />
      </div>

      {finding.requires_clarification ? (
        <p className="mt-2 flex items-start gap-1 rounded border border-red-brand/30 bg-red-wash px-2 py-1.5 text-[11px] text-red-brand">
          <ChevronRight className="mt-0.5 h-3 w-3 shrink-0" aria-hidden />
          Routed to a human reviewer. The engine does not invent a correction when approved
          evidence is missing, expired or in conflict.
        </p>
      ) : (
        finding.suggested_correction && (
          <p className="mt-2 text-[12px] text-ink">
            <span className="text-ink-faint">Suggested correction: </span>
            <span className="font-medium">{finding.suggested_correction}</span>
          </p>
        )
      )}

      {finding.confidence && (
        <p className="mt-1 text-[10px] text-ink-faint">Confidence: {finding.confidence}</p>
      )}
    </div>
  );
}

export function SeveritySummary({ findings }: { findings: Finding[] }) {
  const order: Severity[] = ["Critical", "Major", "Minor", "Information"];
  const counts = order.map((severity) => ({
    severity,
    count: findings.filter((f) => f.severity === severity).length,
  }));
  const clarifications = findings.filter((f) => f.requires_clarification).length;
  const humanReview = findings.filter((f) => f.needs_human_review).length;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {counts
        .filter((entry) => entry.count > 0)
        .map((entry) => (
          <span key={entry.severity} className="inline-flex items-center gap-1 text-[11px] text-ink-soft">
            <SeverityTag severity={entry.severity} />
            <span>{entry.count}</span>
          </span>
        ))}
      {clarifications > 0 && (
        <span className="rounded border border-red-brand/30 bg-red-wash px-1.5 py-0.5 text-[11px] text-red-brand">
          {clarifications} clarification{clarifications === 1 ? "" : "s"}
        </span>
      )}
      {humanReview > 0 && (
        <span className="rounded border border-amber-brand/40 bg-amber-wash px-1.5 py-0.5 text-[11px] text-amber-brand">
          {humanReview} flagged for human review
        </span>
      )}
    </div>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";
import { CheckCheck, FileText, Inbox } from "lucide-react";

import {
  DataTable,
  PageHeader,
  StatusTag,
  Td,
  Th,
  TableSkeleton,
  EmptyState,
  ErrorNote,
} from "@/components/ui";
import { api, formatDateTime } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Asset, AuditEntry, Fact, Guideline, SubmissionSummary, Term } from "@/lib/types";

interface Counts {
  factsApproved: number;
  factsPending: number;
  terms: number;
  guidelines: number;
  assets: number;
  submissionsOpen: number;
  submissionsAwaiting: number;
}

const TERMINAL = ["Approved", "Rejected"];
const REVIEW_QUEUE = ["Submitted", "Resubmitted", "Under Analysis", "Clarification Required"];

export default function DashboardOverview() {
  const { me, role, orgId } = useAuth();
  const [counts, setCounts] = useState<Counts | null>(null);
  const [audit, setAudit] = useState<AuditEntry[] | null>(null);
  const [auditError, setAuditError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!orgId) return;
    setLoading(true);
    try {
      const [facts, terms, guidelines, assets, submissions] = await Promise.all([
        api<Fact[]>("/api/brand/facts"),
        api<Term[]>("/api/brand/terminology"),
        api<Guideline[]>("/api/brand/guidelines"),
        api<Asset[]>("/api/brand/assets"),
        api<SubmissionSummary[]>("/api/submissions"),
      ]);
      setCounts({
        factsApproved: facts.filter((f) => f.approval_status === "approved").length,
        factsPending: facts.filter((f) => f.approval_status === "pending").length,
        terms: terms.length,
        guidelines: guidelines.length,
        assets: assets.length,
        submissionsOpen: submissions.filter((s) => !TERMINAL.includes(s.status)).length,
        submissionsAwaiting: submissions.filter((s) => REVIEW_QUEUE.includes(s.status)).length,
      });
      if (role === "admin" || role === "reviewer") {
        try {
          setAudit(await api<AuditEntry[]>("/api/audit?limit=8"));
        } catch (err) {
          setAuditError(err instanceof Error ? err.message : "Could not load audit trail");
        }
      }
    } catch {
      setCounts(null);
    } finally {
      setLoading(false);
    }
  }, [orgId, role]);

  useEffect(() => {
    void load();
  }, [load]);

  const membership = me?.memberships.find((m) => m.org_id === orgId);

  return (
    <div>
      <PageHeader
        title={membership?.org_name ?? "Overview"}
        description={`Signed in as ${me?.user.full_name} · role: ${role ?? "—"}. All data shown is fictional demo data.`}
      />

      {loading && <TableSkeleton rows={5} cols={2} />}

      {!loading && counts && (
        <div className="rounded border border-hairline bg-white">
          <dl className="divide-y divide-hairline">
            {[
              ["Approved facts", counts.factsApproved, "Confirmed by an admin"],
              ["Facts awaiting confirmation", counts.factsPending, "Pending admin review"],
              ["Open submissions", counts.submissionsOpen, "Drafts, in review and revisions"],
              ["Awaiting human review", counts.submissionsAwaiting, "In the review queue"],
              ["Terminology rules", counts.terms, "Required and prohibited terms"],
              ["Guideline documents", counts.guidelines, "Uploaded TXT / PDF / DOCX"],
              ["Brand assets", counts.assets, "Logos and colours"],
            ].map(([label, value, note]) => (
              <div key={String(label)} className="flex items-baseline justify-between gap-4 px-4 py-3">
                <div>
                  <dt className="text-[13px] text-ink">{label}</dt>
                  <dd className="text-[11px] text-ink-faint">{note}</dd>
                </div>
                <span className="font-serif text-[22px] text-ink">{String(value)}</span>
              </div>
            ))}
          </dl>
        </div>
      )}

      {!loading && !counts && (
        <ErrorNote>Could not load workspace data. Please refresh the page.</ErrorNote>
      )}

      <h2 className="mb-3 mt-8 font-serif text-[17px] text-ink">Recent activity</h2>
      {role === "admin" || role === "reviewer" ? (
        <>
          {audit === null && !auditError && <TableSkeleton rows={4} cols={3} />}
          {auditError && (
            <EmptyState icon={<Inbox className="h-5 w-5" />} title="Audit trail unavailable" description={auditError} />
          )}
          {audit !== null &&
            (audit.length === 0 ? (
              <EmptyState
                icon={<FileText className="h-5 w-5" />}
                title="No activity recorded yet"
                description="Create facts, upload guidelines or manage members and the audit trail will appear here."
              />
            ) : (
              <DataTable>
                <thead>
                  <tr>
                    <Th>Action</Th>
                    <Th>Entity</Th>
                    <Th>Ref</Th>
                    <Th>By</Th>
                    <Th>When</Th>
                  </tr>
                </thead>
                <tbody>
                  {audit.map((row) => (
                    <tr key={row.id}>
                      <Td className="font-mono text-[12px]">{row.action}</Td>
                      <Td>{row.entity_type}</Td>
                      <Td className="text-ink-soft">#{row.entity_id ?? "—"}</Td>
                      <Td>{row.user_email ?? "system"}</Td>
                      <Td className="whitespace-nowrap text-ink-soft">{formatDateTime(row.created_at)}</Td>
                    </tr>
                  ))}
                </tbody>
              </DataTable>
            ))}
        </>
      ) : (
        <EmptyState
          icon={<CheckCheck className="h-5 w-5" />}
          title="Audit access is restricted"
          description="Only admins and reviewers can browse the audit trail."
        />
      )}
    </div>
  );
}

"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ClipboardCheck, ListChecks } from "lucide-react";

import {
  DataTable,
  EmptyState,
  ErrorNote,
  PageHeader,
  StatusTag,
  TableSkeleton,
  Td,
  Th,
} from "@/components/ui";
import { api, formatDateTime } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { SubmissionSummary } from "@/lib/types";

export default function ReviewsPage() {
  const { role, orgId } = useAuth();
  const [queue, setQueue] = useState<SubmissionSummary[] | null>(null);
  const [decided, setDecided] = useState<SubmissionSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!orgId) return;
    if (role !== "admin" && role !== "reviewer") return;
    try {
      const [queueRows, decidedRows] = await Promise.all([
        api<SubmissionSummary[]>("/api/reviews/queue"),
        api<SubmissionSummary[]>("/api/reviews/decided"),
      ]);
      setQueue(queueRows);
      setDecided(decidedRows);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the review queue");
    }
  }, [orgId, role]);

  useEffect(() => {
    void load();
  }, [load]);

  if (role !== null && role !== "admin" && role !== "reviewer") {
    return (
      <EmptyState
        icon={<ClipboardCheck className="h-5 w-5" />}
        title="Review access is restricted"
        description="Only admins and reviewers can open the review queue."
      />
    );
  }

  return (
    <div>
      <PageHeader
        title="Review queue"
        description="Submissions that need a human decision. Approval is never automatic."
      />

      {error && <ErrorNote>{error}</ErrorNote>}

      <h2 className="mb-2 font-serif text-[17px] text-ink">Awaiting review</h2>
      {queue === null && !error && <TableSkeleton rows={3} cols={5} />}
      {queue !== null && queue.length === 0 && (
        <EmptyState
          icon={<ClipboardCheck className="h-5 w-5" />}
          title="Queue is clear"
          description="No submissions are waiting for review right now."
        />
      )}
      {queue !== null && queue.length > 0 && (
        <DataTable>
          <thead>
            <tr>
              <Th>Title</Th>
              <Th>Type</Th>
              <Th>Status</Th>
              <Th>Author</Th>
              <Th>Findings</Th>
              <Th>Updated</Th>
            </tr>
          </thead>
          <tbody>
            {queue.map((row) => (
              <tr key={row.id}>
                <Td>
                  <Link href={`/dashboard/reviews/${row.id}`} className="font-medium text-teal-dark hover:underline">
                    {row.title}
                  </Link>
                </Td>
                <Td className="whitespace-nowrap capitalize">{row.submission_type.replace("_", " ")}</Td>
                <Td>
                  <StatusTag status={row.status} />
                </Td>
                <Td className="text-[12px] text-ink-soft">{row.created_by_email ?? "—"}</Td>
                <Td>
                  {row.latest_finding_count ?? 0}
                  {row.latest_clarification_count ? (
                    <span className="ml-1 text-red-brand">({row.latest_clarification_count} clarification)</span>
                  ) : null}
                </Td>
                <Td className="whitespace-nowrap text-[12px] text-ink-soft">{formatDateTime(row.updated_at)}</Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}

      <h2 className="mb-2 mt-8 font-serif text-[17px] text-ink">Recently decided</h2>
      {decided === null && !error && <TableSkeleton rows={3} cols={4} />}
      {decided !== null && decided.length === 0 && (
        <EmptyState
          icon={<ListChecks className="h-5 w-5" />}
          title="No decisions yet"
          description="Approved and rejected submissions will appear here."
        />
      )}
      {decided !== null && decided.length > 0 && (
        <DataTable>
          <thead>
            <tr>
              <Th>Title</Th>
              <Th>Status</Th>
              <Th>Author</Th>
              <Th>Updated</Th>
            </tr>
          </thead>
          <tbody>
            {decided.map((row) => (
              <tr key={row.id}>
                <Td>
                  <Link href={`/dashboard/reviews/${row.id}`} className="font-medium text-teal-dark hover:underline">
                    {row.title}
                  </Link>
                </Td>
                <Td>
                  <StatusTag status={row.status} />
                </Td>
                <Td className="text-[12px] text-ink-soft">{row.created_by_email ?? "—"}</Td>
                <Td className="whitespace-nowrap text-[12px] text-ink-soft">{formatDateTime(row.updated_at)}</Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
    </div>
  );
}

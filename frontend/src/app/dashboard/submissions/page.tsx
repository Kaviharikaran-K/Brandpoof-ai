"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { FilePlus2, FileStack } from "lucide-react";

import {
  Button,
  DataTable,
  EmptyState,
  ErrorNote,
  PageHeader,
  Select,
  StatusTag,
  TableSkeleton,
  Td,
  Th,
} from "@/components/ui";
import { api, formatDateTime } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { SubmissionSummary } from "@/lib/types";

const STATUS_OPTIONS = [
  "Draft",
  "Submitted",
  "Under Analysis",
  "Changes Requested",
  "Clarification Required",
  "Resubmitted",
  "Approved",
  "Rejected",
];

export default function SubmissionsPage() {
  const { role, orgId } = useAuth();
  const [submissions, setSubmissions] = useState<SubmissionSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");

  const canCreate = role === "admin" || role === "creator";

  const load = useCallback(async () => {
    if (!orgId) return;
    try {
      const query = statusFilter ? `?status_filter=${encodeURIComponent(statusFilter)}` : "";
      setSubmissions(await api<SubmissionSummary[]>(`/api/submissions${query}`));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load submissions");
    }
  }, [orgId, statusFilter]);

  useEffect(() => {
    setSubmissions(null);
    void load();
  }, [load]);

  return (
    <div>
      <PageHeader
        title="Submissions"
        description="Content checked against approved facts, terminology and tone before a human approves it."
        actions={
          canCreate ? (
            <Link href="/dashboard/submissions/new">
              <Button variant="primary">
                <FilePlus2 className="h-3.5 w-3.5" aria-hidden /> New submission
              </Button>
            </Link>
          ) : undefined
        }
      />

      <div className="mb-4 flex items-center gap-3">
        <label htmlFor="submission-filter" className="text-[12px] text-ink-soft">
          Status
        </label>
        <Select
          id="submission-filter"
          className="w-52"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All</option>
          {STATUS_OPTIONS.map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </Select>
      </div>

      {error && <ErrorNote>{error}</ErrorNote>}

      {submissions === null && !error && <TableSkeleton rows={5} cols={6} />}

      {submissions !== null &&
        (submissions.length === 0 ? (
          <EmptyState
            icon={<FileStack className="h-5 w-5" />}
            title="No submissions yet"
            description={
              canCreate
                ? "Submit marketing copy and the engine will compare every claim against your approved facts."
                : "Creators have not submitted any content in this organisation yet."
            }
            action={
              canCreate ? (
                <Link href="/dashboard/submissions/new">
                  <Button variant="primary">
                    <FilePlus2 className="h-3.5 w-3.5" aria-hidden /> Create the first submission
                  </Button>
                </Link>
              ) : undefined
            }
          />
        ) : (
          <DataTable>
            <thead>
              <tr>
                <Th>Title</Th>
                <Th>Type</Th>
                <Th>Status</Th>
                <Th>Author</Th>
                <Th>Revision</Th>
                <Th>Findings</Th>
                <Th>Updated</Th>
              </tr>
            </thead>
            <tbody>
              {submissions.map((row) => (
                <tr key={row.id}>
                  <Td>
                    <Link
                      href={`/dashboard/submissions/${row.id}`}
                      className="font-medium text-teal-dark hover:underline"
                    >
                      {row.title}
                    </Link>
                  </Td>
                  <Td className="whitespace-nowrap capitalize">{row.submission_type.replace("_", " ")}</Td>
                  <Td>
                    <StatusTag status={row.status} />
                  </Td>
                  <Td className="text-[12px] text-ink-soft">{row.created_by_email ?? "—"}</Td>
                  <Td className="whitespace-nowrap">v{row.current_revision_number ?? "—"}</Td>
                  <Td className="whitespace-nowrap">
                    {row.latest_finding_count === null ? (
                      <span className="text-ink-faint">Not analysed</span>
                    ) : (
                      <span>
                        {row.latest_finding_count}
                        {row.latest_clarification_count ? (
                          <span className="ml-1 text-red-brand">
                            ({row.latest_clarification_count} clarification
                            {row.latest_clarification_count === 1 ? "" : "s"})
                          </span>
                        ) : null}
                      </span>
                    )}
                  </Td>
                  <Td className="whitespace-nowrap text-[12px] text-ink-soft">
                    {formatDateTime(row.updated_at)}
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        ))}
    </div>
  );
}

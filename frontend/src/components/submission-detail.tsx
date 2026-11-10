"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Check, MessageSquare, Play, X } from "lucide-react";

import {
  Button,
  DataTable,
  Dialog,
  EmptyState,
  ErrorNote,
  Field,
  PageHeader,
  StatusTag,
  TableSkeleton,
  Td,
  Textarea,
  Th,
} from "@/components/ui";
import { FindingCard, HighlightedText, SeveritySummary } from "@/components/findings";
import { VisualReportPanel } from "@/components/visual-report";
import { useToast } from "@/components/toast";
import { api, formatDateTime } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { SubmissionDetail } from "@/lib/types";

type Decision = "approve" | "reject" | "request-changes" | "request-clarification";

const TERMINAL = ["Approved", "Rejected"];
const DECIDABLE = ["Submitted", "Resubmitted", "Clarification Required"];

const DECISION_TITLE: Record<Decision, string> = {
  approve: "Approve submission",
  reject: "Reject submission",
  "request-changes": "Request changes",
  "request-clarification": "Request clarification",
};

const DECISION_HINT: Record<Decision, string> = {
  approve: "Optional note recorded in the audit trail.",
  reject: "A note is required so the author understands the decision.",
  "request-changes": "A note is required and is shown to the author.",
  "request-clarification": "A note is required and is shown to the author.",
};

const NOTE_REQUIRED: Decision[] = ["reject", "request-changes", "request-clarification"];

export function SubmissionDetailView({
  submissionId,
  backHref = "/dashboard/submissions",
}: {
  submissionId: number;
  backHref?: string;
}) {
  const { me, role } = useAuth();
  const toast = useToast();
  const [detail, setDetail] = useState<SubmissionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [activeFinding, setActiveFinding] = useState<number | null>(null);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [note, setNote] = useState("");
  const [comment, setComment] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setDetail(await api<SubmissionDetail>(`/api/submissions/${submissionId}`));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the submission");
    }
  }, [submissionId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function runAnalysis() {
    setBusy("analyse");
    try {
      await api(`/api/submissions/${submissionId}/analyse`, { method: "POST" });
      toast.success("Analysis complete", "The findings below reflect the current revision.");
      await load();
    } catch (err) {
      toast.error("Analysis failed", err instanceof Error ? err.message : undefined);
    } finally {
      setBusy(null);
    }
  }

  async function submitDecision() {
    if (!decision) return;
    setBusy("decision");
    setActionError(null);
    try {
      await api(`/api/reviews/${submissionId}/${decision}`, {
        method: "POST",
        body: JSON.stringify({ note }),
      });
      toast.success(
        decision === "approve"
          ? "Submission approved"
          : decision === "reject"
            ? "Submission rejected"
            : "Decision recorded"
      );
      setDecision(null);
      setNote("");
      await load();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Could not record the decision");
    } finally {
      setBusy(null);
    }
  }

  async function submitComment(e: React.FormEvent) {
    e.preventDefault();
    if (!comment.trim()) return;
    setBusy("comment");
    try {
      await api(`/api/reviews/${submissionId}/comment`, {
        method: "POST",
        body: JSON.stringify({ body: comment.trim() }),
      });
      setComment("");
      toast.success("Comment added");
      await load();
    } catch (err) {
      toast.error("Could not add the comment", err instanceof Error ? err.message : undefined);
    } finally {
      setBusy(null);
    }
  }

  if (error) {
    return (
      <div>
        <Link href={backHref} className="mb-3 inline-flex items-center gap-1 text-[12px] text-teal">
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden /> Back
        </Link>
        <ErrorNote>{error}</ErrorNote>
      </div>
    );
  }

  if (!detail) {
    return (
      <div>
        <div className="skeleton mb-4 h-8 w-64" />
        <TableSkeleton rows={6} cols={3} />
      </div>
    );
  }

  const latestRun = detail.runs[0] ?? null;
  const findings = latestRun?.findings ?? [];
  const latestRevision =
    detail.revisions.find((rev) => rev.id === latestRun?.revision_id) ??
    detail.revisions[detail.revisions.length - 1] ??
    null;
  const isOwner = me ? detail.created_by_id === me.user.id : false;
  const closed = TERMINAL.includes(detail.status);
  const canEdit =
    !closed && detail.status !== "Under Analysis" && (role === "admin" || (role === "creator" && isOwner));
  const canReview = role === "admin" || role === "reviewer";
  const decidable = DECIDABLE.includes(detail.status);
  const clarificationOnly = detail.status === "Changes Requested";

  return (
    <div>
      <Link href={backHref} className="mb-3 inline-flex items-center gap-1 text-[12px] text-teal">
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden /> Back
      </Link>

      <PageHeader
        title={detail.title}
        description={`${detail.submission_type.replace("_", " ")} · submitted by ${detail.created_by_email ?? "unknown"} · ${
          detail.revisions.length
        } revision${detail.revisions.length === 1 ? "" : "s"} · updated ${formatDateTime(detail.updated_at)}`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {canEdit && (
              <Button
                variant="primary"
                onClick={() => void runAnalysis()}
                loading={busy === "analyse"}
                disabled={detail.status === "Under Analysis"}
              >
                <Play className="h-3.5 w-3.5" aria-hidden /> Run analysis
              </Button>
            )}
            {canEdit && (
              <Link href={`/dashboard/submissions/${detail.id}/revise`}>
                <Button>Create revision</Button>
              </Link>
            )}
            {canReview && (decidable || clarificationOnly) && (
              <>
                {decidable && (
                  <>
                    <Button variant="primary" onClick={() => setDecision("approve")}>
                      <Check className="h-3.5 w-3.5" aria-hidden /> Approve
                    </Button>
                    <Button onClick={() => setDecision("request-changes")}>Request changes</Button>
                    <Button onClick={() => setDecision("request-clarification")}>
                      Request clarification
                    </Button>
                    <Button variant="danger" onClick={() => setDecision("reject")}>
                      <X className="h-3.5 w-3.5" aria-hidden /> Reject
                    </Button>
                  </>
                )}
                {clarificationOnly && (
                  <Button onClick={() => setDecision("request-clarification")}>
                    Request clarification
                  </Button>
                )}
              </>
            )}
          </div>
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <StatusTag status={detail.status} />
        {latestRun && (
          <span className="font-mono text-[11px] text-ink-faint">
            {latestRun.engine} · run #{latestRun.id} · {latestRun.finding_count} finding
            {latestRun.finding_count === 1 ? "" : "s"}
          </span>
        )}
        {detail.decided_at && (
          <span className="text-[11px] text-ink-soft">Decided {formatDateTime(detail.decided_at)}</span>
        )}
        {detail.status === "Draft" && (
          <span className="text-[11px] text-ink-soft">
            Draft — run the analysis to submit it for review.
          </span>
        )}
      </div>

      {detail.has_image && (
        <div className="mb-4 rounded border border-hairline bg-white p-3">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-ink-faint">
            Attached visual · {detail.image_name}
          </p>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={`/api/submissions/${detail.id}/image`}
            alt={detail.alt_text || `Attachment for ${detail.title}`}
            className="max-h-64 rounded border border-hairline object-contain"
          />
          <p className="mt-2 text-[11px] text-ink-faint">
            {detail.alt_text ? `Alt text: ${detail.alt_text}` : "No alt text supplied — flagged for accessibility review."}
          </p>
          {latestRun?.visual_report && <VisualReportPanel report={latestRun.visual_report} />}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <div className="rounded border border-hairline bg-white p-4">
            <div className="mb-2 flex items-center justify-between gap-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-faint">
                Revision {latestRevision?.revision_number ?? "—"} · content
              </p>
              {latestRevision && (
                <span className="text-[11px] text-ink-faint">{formatDateTime(latestRevision.created_at)}</span>
              )}
            </div>
            {latestRevision ? (
              <HighlightedText
                content={latestRevision.content}
                findings={findings}
                activeId={activeFinding}
              />
            ) : (
              <p className="text-[13px] text-ink-soft">No content recorded.</p>
            )}
            <p className="mt-3 border-t border-hairline pt-2 text-[11px] text-ink-faint">
              Highlights map each finding to the exact text it applies to. Hover a finding to
              locate it.
            </p>
          </div>

          {detail.revisions.length > 1 && (
            <div className="mt-4 rounded border border-hairline bg-white">
              <p className="border-b border-hairline px-4 py-2 text-[11px] font-semibold uppercase tracking-wide text-ink-faint">
                Revision history
              </p>
              <div className="divide-y divide-hairline">
                {[...detail.revisions].reverse().map((rev) => (
                  <details key={rev.id} className="px-4 py-2">
                    <summary className="cursor-pointer text-[12px] text-ink">
                      Revision {rev.revision_number}
                      <span className="ml-2 text-ink-faint">{formatDateTime(rev.created_at)}</span>
                    </summary>
                    <p className="mt-2 whitespace-pre-wrap text-[12px] text-ink-soft">{rev.content}</p>
                  </details>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="lg:col-span-2">
          <div className="rounded border border-hairline bg-white p-4">
            <div className="mb-3 flex items-center justify-between gap-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-faint">
                Findings
              </p>
              {findings.length > 0 && <SeveritySummary findings={findings} />}
            </div>

            {!latestRun && (
              <EmptyState
                icon={<Play className="h-5 w-5" />}
                title="No analysis yet"
                description={
                  canEdit
                    ? "Run the analysis to check this submission against the approved evidence base."
                    : "The creator has not run the analysis on this revision yet."
                }
              />
            )}

            {latestRun && findings.length === 0 && (
              <div className="rounded border border-teal/30 bg-teal-wash px-3 py-3 text-[12px] text-teal-dark">
                No issues detected in this revision. Every claim matches approved evidence and no
                terminology or tone rules were triggered.
              </div>
            )}

            {findings.length > 0 && (
              <div className="space-y-2">
                {findings.map((finding) => (
                  <FindingCard
                    key={finding.id}
                    finding={finding}
                    active={activeFinding === finding.id}
                    onHover={setActiveFinding}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <div className="rounded border border-hairline bg-white">
          <p className="border-b border-hairline px-4 py-2 text-[11px] font-semibold uppercase tracking-wide text-ink-faint">
            Review comments
          </p>
          <div className="divide-y divide-hairline">
            {detail.comments.length === 0 && (
              <p className="px-4 py-3 text-[12px] text-ink-soft">No comments yet.</p>
            )}
            {detail.comments.map((row) => (
              <div key={row.id} className="px-4 py-2.5">
                <p className="text-[11px] text-ink-faint">
                  {row.author_name} ({row.author_email}) · {formatDateTime(row.created_at)}
                </p>
                <p className="mt-1 whitespace-pre-wrap text-[13px] text-ink">{row.body}</p>
              </div>
            ))}
          </div>
          {!closed && (
            <form onSubmit={submitComment} className="border-t border-hairline p-3">
              <Field label="Add a comment" htmlFor="comment-body">
                <Textarea
                  id="comment-body"
                  rows={2}
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="Ask a question or note a required fix…"
                />
              </Field>
              <div className="mt-2 flex justify-end">
                <Button
                  type="submit"
                  size="sm"
                  loading={busy === "comment"}
                  disabled={!comment.trim()}
                >
                  <MessageSquare className="h-3 w-3" aria-hidden /> Add comment
                </Button>
              </div>
            </form>
          )}
        </div>

        <div className="rounded border border-hairline bg-white">
          <p className="border-b border-hairline px-4 py-2 text-[11px] font-semibold uppercase tracking-wide text-ink-faint">
            Approval decisions
          </p>
          {detail.decisions.length === 0 ? (
            <p className="px-4 py-3 text-[12px] text-ink-soft">
              No decision recorded. Approval always requires a human reviewer.
            </p>
          ) : (
            <DataTable className="border-0">
              <thead>
                <tr>
                  <Th>Decision</Th>
                  <Th>Transition</Th>
                  <Th>By</Th>
                  <Th>When</Th>
                </tr>
              </thead>
              <tbody>
                {detail.decisions.map((row) => (
                  <tr key={row.id}>
                    <Td className="font-mono text-[12px]">
                      {row.decision}
                      {row.note && (
                        <span className="mt-1 block max-w-xs whitespace-pre-wrap font-sans text-[11px] text-ink-soft">
                          {row.note}
                        </span>
                      )}
                    </Td>
                    <Td className="text-[12px] text-ink-soft">
                      {row.from_status} → {row.to_status}
                    </Td>
                    <Td className="text-[12px]">{row.decided_by_email}</Td>
                    <Td className="whitespace-nowrap text-[12px] text-ink-soft">
                      {formatDateTime(row.decided_at)}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </DataTable>
          )}
        </div>
      </div>

      <Dialog
        open={decision !== null}
        onClose={() => {
          setDecision(null);
          setActionError(null);
        }}
        title={decision ? DECISION_TITLE[decision] : "Decision"}
      >
        {decision && (
          <div className="space-y-3">
            <p className="text-[12px] text-ink-soft">{DECISION_HINT[decision]}</p>
            {actionError && <ErrorNote>{actionError}</ErrorNote>}
            <Field
              label={NOTE_REQUIRED.includes(decision) ? "Note (required)" : "Note (optional)"}
              htmlFor="decision-note"
            >
              <Textarea
                id="decision-note"
                rows={3}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Explain the decision for the audit trail…"
              />
            </Field>
            <div className="flex justify-end gap-2 border-t border-hairline pt-3">
              <Button
                onClick={() => {
                  setDecision(null);
                  setActionError(null);
                }}
              >
                Cancel
              </Button>
              <Button
                variant={decision === "reject" ? "danger" : "primary"}
                onClick={() => void submitDecision()}
                loading={busy === "decision"}
                disabled={NOTE_REQUIRED.includes(decision) && !note.trim()}
              >
                {DECISION_TITLE[decision]}
              </Button>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
}

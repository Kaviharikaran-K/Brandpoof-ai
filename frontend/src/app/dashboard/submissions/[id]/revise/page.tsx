"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, FileUp } from "lucide-react";

import {
  Button,
  Card,
  ErrorNote,
  Field,
  Input,
  PageHeader,
  StatusTag,
  TableSkeleton,
  Textarea,
} from "@/components/ui";
import { SeverityTag } from "@/components/findings";
import { useToast } from "@/components/toast";
import { api, formatDateTime } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { SubmissionDetail } from "@/lib/types";

const TERMINAL = ["Approved", "Rejected"];

export default function ReviseSubmissionPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const { role, orgId, me } = useAuth();
  const router = useRouter();
  const toast = useToast();
  const [detail, setDetail] = useState<SubmissionDetail | null>(null);
  const [content, setContent] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const [altText, setAltText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    if (!orgId || !Number.isFinite(id)) return;
    try {
      const data = await api<SubmissionDetail>(`/api/submissions/${id}`);
      setDetail(data);
      const latest = data.revisions[data.revisions.length - 1];
      setContent(latest?.content ?? "");
      setAltText(data.alt_text ?? "");
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the submission");
    }
  }, [orgId, id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const form = new FormData();
      form.set("content", content);
      if (image) form.set("image", image);
      form.set("alt_text", altText.trim());
      await api(`/api/submissions/${id}/revise`, { method: "POST", body: form });
      toast.success("Revision saved and re-analysed", "The latest findings are shown on the submission.");
      router.push(`/dashboard/submissions/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the revision");
    } finally {
      setSaving(false);
    }
  }

  if (error && !detail) {
    return (
      <div>
        <Link href={`/dashboard/submissions/${id}`} className="mb-3 inline-flex items-center gap-1 text-[12px] text-teal">
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
        <TableSkeleton rows={5} cols={2} />
      </div>
    );
  }

  const isOwner = me ? detail.created_by_id === me.user.id : false;
  const canEdit = role === "admin" || (role === "creator" && isOwner);
  const closed = TERMINAL.includes(detail.status);
  const latestRun = detail.runs[0] ?? null;
  const openIssues = (latestRun?.findings ?? []).filter((f) => !f.requires_clarification);
  const clarifications = (latestRun?.findings ?? []).filter((f) => f.requires_clarification);

  if (!canEdit || closed) {
    return (
      <div>
        <Link href={`/dashboard/submissions/${id}`} className="mb-3 inline-flex items-center gap-1 text-[12px] text-teal">
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden /> Back
        </Link>
        <ErrorNote>
          {closed
            ? "This submission is closed and can no longer be revised."
            : "Only the submission author or an admin can create a revision."}
        </ErrorNote>
      </div>
    );
  }

  return (
    <div>
      <Link href={`/dashboard/submissions/${id}`} className="mb-3 inline-flex items-center gap-1 text-[12px] text-teal">
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden /> Back to submission
      </Link>

      <PageHeader
        title={`Revise: ${detail.title}`}
        description={`Editing revision ${detail.revisions.length}. Saving creates a new revision and immediately re-runs the analysis.`}
        actions={<StatusTag status={detail.status} />}
      />

      {latestRun && (openIssues.length > 0 || clarifications.length > 0) && (
        <Card className="mb-4 p-4">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-ink-faint">
            Findings in the current revision
          </p>
          <div className="space-y-2">
            {openIssues.map((finding) => (
              <div key={finding.id} className="flex flex-wrap items-center gap-2 text-[12px]">
                <SeverityTag severity={finding.severity} />
                <span className="text-ink">{finding.category}</span>
                <span className="font-mono text-[11px] text-ink-soft">“{finding.detected_text}”</span>
                {finding.suggested_correction && (
                  <span className="text-ink-soft">→ {finding.suggested_correction}</span>
                )}
              </div>
            ))}
            {clarifications.map((finding) => (
              <div key={finding.id} className="flex flex-wrap items-center gap-2 text-[12px]">
                <SeverityTag severity={finding.severity} />
                <span className="hatched rounded px-1 text-red-brand">Needs clarification</span>
                <span className="font-mono text-[11px] text-ink-soft">“{finding.detected_text}”</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card className="p-5">
        <form onSubmit={handleSubmit} className="grid gap-4" noValidate>
          {error && <ErrorNote>{error}</ErrorNote>}
          <Field
            label="Revised content"
            htmlFor="revision-content"
            hint={`${content.length.toLocaleString("en-GB")} / 50,000 characters · previous revision saved ${formatDateTime(
              detail.revisions[detail.revisions.length - 1]?.created_at
            )}`}
          >
            <Textarea
              id="revision-content"
              rows={12}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              required
              maxLength={50000}
            />
          </Field>

          <Field label="Replace attached visual (optional)" htmlFor="revision-image">
            <input
              id="revision-image"
              type="file"
              accept="image/png,image/jpeg,image/svg+xml,image/webp"
              onChange={(e) => setImage(e.target.files?.[0] ?? null)}
              className="w-full rounded border border-hairline bg-white px-2.5 py-1.5 text-[12px] text-ink-soft file:mr-3 file:rounded file:border-0 file:bg-paper file:px-2 file:py-1 file:text-[12px] file:text-ink"
            />
          </Field>

          <Field
            label="Alt text"
            htmlFor="revision-alt"
            hint={`${altText.length} / 500 characters. Describe any attached visual for screen readers.`}
          >
            <Input
              id="revision-alt"
              value={altText}
              onChange={(e) => setAltText(e.target.value)}
              maxLength={500}
              placeholder="NovaCloud logo over a teal gradient with the tagline."
            />
          </Field>

          <div className="flex justify-end gap-2 border-t border-hairline pt-4">
            <Link href={`/dashboard/submissions/${id}`}>
              <Button type="button">Cancel</Button>
            </Link>
            <Button type="submit" variant="primary" loading={saving} disabled={!content.trim()}>
              <FileUp className="h-3.5 w-3.5" aria-hidden /> Save revision and re-analyse
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

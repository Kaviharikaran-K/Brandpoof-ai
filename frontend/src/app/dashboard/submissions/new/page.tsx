"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, FileUp, Play } from "lucide-react";

import { Button, Card, ErrorNote, Field, Input, PageHeader, Select, Textarea } from "@/components/ui";
import { useToast } from "@/components/toast";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { SubmissionDetail } from "@/lib/types";

const TYPES = [
  { value: "ad_copy", label: "Ad copy" },
  { value: "blog_post", label: "Blog post" },
  { value: "email", label: "Email" },
  { value: "social", label: "Social post" },
  { value: "other", label: "Other" },
];

export default function NewSubmissionPage() {
  const { role, orgId } = useAuth();
  const router = useRouter();
  const toast = useToast();
  const [title, setTitle] = useState("");
  const [submissionType, setSubmissionType] = useState("ad_copy");
  const [content, setContent] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const [altText, setAltText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [analyseNow, setAnalyseNow] = useState(true);

  const canCreate = role === "admin" || role === "creator";

  useEffect(() => {
    if (role !== null && !canCreate) {
      router.replace("/dashboard/submissions");
    }
  }, [role, canCreate, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const form = new FormData();
      form.set("title", title.trim());
      form.set("submission_type", submissionType);
      form.set("content", content);
      if (image) {
        form.set("image", image);
        if (altText.trim()) form.set("alt_text", altText.trim());
      }

      const created = await api<SubmissionDetail>("/api/submissions", {
        method: "POST",
        body: form,
      });

      if (analyseNow) {
        try {
          await api(`/api/submissions/${created.id}/analyse`, { method: "POST" });
          toast.success("Submission analysed", "Review the findings against each highlighted claim.");
        } catch (err) {
          toast.error(
            "Saved as a draft, but analysis failed",
            err instanceof Error ? err.message : undefined
          );
        }
      } else {
        toast.success("Draft saved", "Run the analysis when the copy is ready for review.");
      }

      router.push(`/dashboard/submissions/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the submission");
    } finally {
      setSaving(false);
    }
  }

  if (role !== null && !canCreate) {
    return <ErrorNote>Only admins and creators can submit content.</ErrorNote>;
  }

  return (
    <div>
      <Link href="/dashboard/submissions" className="mb-3 inline-flex items-center gap-1 text-[12px] text-teal-dark">
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden /> Back to submissions
      </Link>

      <PageHeader
        title="New submission"
        description="Paste the copy to check. Every claim is matched against approved facts — pending facts never count as evidence."
      />

      <Card className="p-5">
        <form onSubmit={handleSubmit} className="grid gap-4" noValidate>
          {error && <ErrorNote>{error}</ErrorNote>}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Title" htmlFor="submission-title" hint="A short label for reviewers.">
              <Input
                id="submission-title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="NovaCloud spring launch — homepage hero"
                required
                maxLength={200}
              />
            </Field>
            <Field label="Content type" htmlFor="submission-type">
              <Select
                id="submission-type"
                value={submissionType}
                onChange={(e) => setSubmissionType(e.target.value)}
              >
                {TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          <Field
            label="Content"
            htmlFor="submission-content"
            hint={`${content.length.toLocaleString("en-GB")} / 50,000 characters`}
          >
            <Textarea
              id="submission-content"
              rows={10}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Paste the marketing copy here. Keep it exactly as it would be published."
              required
              maxLength={50000}
            />
          </Field>

          <Field
            label="Attached visual (optional)"
            htmlFor="submission-image"
            hint="PNG, JPEG, SVG or WebP, up to the configured upload limit."
          >
            <input
              id="submission-image"
              type="file"
              accept="image/png,image/jpeg,image/svg+xml,image/webp"
              onChange={(e) => setImage(e.target.files?.[0] ?? null)}
              className="w-full rounded border border-hairline bg-white px-2.5 py-1.5 text-[12px] text-ink-soft file:mr-3 file:rounded file:border-0 file:bg-paper file:px-2 file:py-1 file:text-[12px] file:text-ink"
            />
          </Field>

          {image && (
            <Field
              label="Alt text"
              htmlFor="submission-alt"
              hint={`${altText.length} / 500 characters. Describe the visual for screen readers; it is checked for accessibility.`}
            >
              <Input
                id="submission-alt"
                value={altText}
                onChange={(e) => setAltText(e.target.value)}
                placeholder="NovaCloud logo over a teal gradient with the tagline."
                maxLength={500}
              />
            </Field>
          )}

          <label className="flex items-center gap-2 text-[12px] text-ink-soft">
            <input
              type="checkbox"
              checked={analyseNow}
              onChange={(e) => setAnalyseNow(e.target.checked)}
              className="h-3.5 w-3.5 accent-teal"
            />
            <Play className="h-3.5 w-3.5 text-teal" aria-hidden />
            Run the analysis immediately and submit for review
          </label>

          <div className="flex justify-end gap-2 border-t border-hairline pt-4">
            <Link href="/dashboard/submissions">
              <Button type="button">Cancel</Button>
            </Link>
            <Button type="submit" variant="primary" loading={saving} disabled={!title.trim() || !content.trim()}>
              <FileUp className="h-3.5 w-3.5" aria-hidden /> {analyseNow ? "Create and analyse" : "Save draft"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

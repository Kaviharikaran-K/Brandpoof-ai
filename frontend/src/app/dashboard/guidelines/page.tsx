"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Download, FileText, Trash2, Upload } from "lucide-react";

import {
  Button,
  DataTable,
  EmptyState,
  ErrorNote,
  Field,
  Input,
  PageHeader,
  Td,
  Th,
  TableSkeleton,
} from "@/components/ui";
import { useToast } from "@/components/toast";
import { api, formatBytes, formatDateTime } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Guideline } from "@/lib/types";

export default function GuidelinesPage() {
  const { role, orgId } = useAuth();
  const toast = useToast();
  const [guidelines, setGuidelines] = useState<Guideline[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const isAdmin = role === "admin";
  const canUpload = role === "admin" || role === "creator";

  const load = useCallback(async () => {
    if (!orgId) return;
    try {
      setGuidelines(await api<Guideline[]>("/api/brand/guidelines"));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load guidelines");
    }
  }, [orgId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      toast.error("Choose a file first");
      return;
    }
    setUploading(true);
    try {
      const data = new FormData();
      data.set("title", title.trim() || file.name);
      data.set("file", file);
      await api("/api/brand/guidelines", { method: "POST", body: data });
      toast.success("Guideline uploaded");
      setTitle("");
      setFile(null);
      if (fileInput.current) fileInput.current.value = "";
      await load();
    } catch (err) {
      toast.error("Upload failed", err instanceof Error ? err.message : undefined);
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(guideline: Guideline) {
    if (!window.confirm(`Delete "${guideline.title}"?`)) return;
    try {
      await api(`/api/brand/guidelines/${guideline.id}`, { method: "DELETE" });
      toast.success("Guideline deleted");
      await load();
    } catch (err) {
      toast.error("Could not delete", err instanceof Error ? err.message : undefined);
    }
  }

  return (
    <div>
      <PageHeader
        title="Brand guidelines"
        description="Uploaded documents are stored per organisation. Allowed types: TXT, PDF, DOCX (max 10 MB)."
      />

      {canUpload && (
        <form
          onSubmit={handleUpload}
          className="mb-6 flex flex-wrap items-end gap-3 rounded border border-hairline bg-white p-4"
          noValidate
        >
          <div className="min-w-48 flex-1">
            <Field label="Title" htmlFor="guideline-title">
              <Input
                id="guideline-title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="NovaCloud style guide 2025"
              />
            </Field>
          </div>
          <div className="flex-1">
            <Field label="File" htmlFor="guideline-file" hint="TXT, PDF or DOCX">
              <input
                ref={fileInput}
                id="guideline-file"
                type="file"
                accept=".txt,.pdf,.docx"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="w-full rounded border border-hairline bg-white px-2.5 py-1.5 text-[12px] text-ink file:mr-3 file:rounded file:border-0 file:bg-paper file:px-2 file:py-1 file:text-[12px] file:text-ink-soft"
              />
            </Field>
          </div>
          <Button type="submit" variant="primary" loading={uploading}>
            <Upload className="h-3.5 w-3.5" aria-hidden /> Upload
          </Button>
        </form>
      )}

      {error && <ErrorNote>{error}</ErrorNote>}

      {guidelines === null && !error && <TableSkeleton rows={3} cols={5} />}

      {guidelines !== null &&
        (guidelines.length === 0 ? (
          <EmptyState
            icon={<FileText className="h-5 w-5" />}
            title="No guideline documents yet"
            description="Upload your brand guidelines so reviewers and analysis can cite them."
            action={
              canUpload ? undefined : (
                <p className="text-[12px] text-ink-faint">Reviewers have read access; upload rights belong to admins and creators.</p>
              )
            }
          />
        ) : (
          <DataTable>
            <thead>
              <tr>
                <Th>Title</Th>
                <Th>File</Th>
                <Th>Type</Th>
                <Th>Size</Th>
                <Th>Uploaded</Th>
                <Th>Actions</Th>
              </tr>
            </thead>
            <tbody>
              {guidelines.map((g) => (
                <tr key={g.id}>
                  <Td className="font-medium">{g.title}</Td>
                  <Td className="max-w-xs truncate font-mono text-[12px] text-ink-soft">{g.file_name}</Td>
                  <Td className="whitespace-nowrap text-ink-soft">{g.content_type}</Td>
                  <Td className="whitespace-nowrap">{formatBytes(g.size_bytes)}</Td>
                  <Td className="whitespace-nowrap text-ink-soft">{formatDateTime(g.created_at)}</Td>
                  <Td>
                    <div className="flex items-center gap-1">
                      <a
                        href={`/api/brand/guidelines/${g.id}/download`}
                        className="inline-flex items-center gap-1 rounded border border-hairline bg-white px-2.5 py-1 text-[12px] text-ink transition-colors hover:border-ink-faint"
                      >
                        <Download className="h-3 w-3" aria-hidden /> Download
                      </a>
                      {isAdmin && (
                        <Button size="sm" variant="danger" onClick={() => void handleDelete(g)}>
                          <Trash2 className="h-3 w-3" aria-hidden />
                        </Button>
                      )}
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        ))}
    </div>
  );
}

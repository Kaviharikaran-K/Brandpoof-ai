"use client";

import { useCallback, useEffect, useState } from "react";
import { CaseSensitive, Pencil, Plus, Trash2 } from "lucide-react";

import {
  Button,
  DataTable,
  Dialog,
  EmptyState,
  ErrorNote,
  Field,
  Input,
  PageHeader,
  Select,
  Td,
  Textarea,
  Th,
  TableSkeleton,
} from "@/components/ui";
import { useToast } from "@/components/toast";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Term } from "@/lib/types";

interface TermForm {
  rule_type: "required" | "prohibited";
  term: string;
  description: string;
}

const emptyForm: TermForm = { rule_type: "required", term: "", description: "" };

export default function TerminologyPage() {
  const { role, orgId } = useAuth();
  const toast = useToast();
  const [terms, setTerms] = useState<Term[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Term | null>(null);
  const [form, setForm] = useState<TermForm>(emptyForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const isAdmin = role === "admin";

  const load = useCallback(async () => {
    if (!orgId) return;
    try {
      setTerms(await api<Term[]>("/api/brand/terminology"));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load terminology");
    }
  }, [orgId]);

  useEffect(() => {
    void load();
  }, [load]);

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setFormError(null);
    setDialogOpen(true);
  }

  function openEdit(term: Term) {
    setEditing(term);
    setForm({ rule_type: term.rule_type, term: term.term, description: term.description });
    setFormError(null);
    setDialogOpen(true);
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSaving(true);
    try {
      if (editing) {
        await api(`/api/brand/terminology/${editing.id}`, {
          method: "PUT",
          body: JSON.stringify({ ...form, term: form.term.trim() }),
        });
        toast.success("Terminology rule updated");
      } else {
        await api("/api/brand/terminology", {
          method: "POST",
          body: JSON.stringify({ ...form, term: form.term.trim() }),
        });
        toast.success("Terminology rule added");
      }
      setDialogOpen(false);
      await load();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not save the rule");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(term: Term) {
    if (!window.confirm(`Delete the ${term.rule_type} term "${term.term}"?`)) return;
    try {
      await api(`/api/brand/terminology/${term.id}`, { method: "DELETE" });
      toast.success("Terminology rule deleted");
      await load();
    } catch (err) {
      toast.error("Could not delete rule", err instanceof Error ? err.message : undefined);
    }
  }

  return (
    <div>
      <PageHeader
        title="Terminology"
        description="Required and prohibited terms. Checks are word-boundary and case-insensitive."
        actions={
          isAdmin ? (
            <Button variant="primary" onClick={openCreate}>
              <Plus className="h-3.5 w-3.5" aria-hidden /> Add rule
            </Button>
          ) : undefined
        }
      />

      {error && <ErrorNote>{error}</ErrorNote>}

      {terms === null && !error && <TableSkeleton rows={3} cols={3} />}

      {terms !== null &&
        (terms.length === 0 ? (
          <EmptyState
            icon={<CaseSensitive className="h-5 w-5" />}
            title="No terminology rules yet"
            description="Add the words your brand requires and the words it prohibits."
            action={
              isAdmin ? (
                <Button variant="primary" onClick={openCreate}>
                  <Plus className="h-3.5 w-3.5" aria-hidden /> Add the first rule
                </Button>
              ) : undefined
            }
          />
        ) : (
          <DataTable>
            <thead>
              <tr>
                <Th>Rule</Th>
                <Th>Term</Th>
                <Th>Guidance</Th>
                {isAdmin && <Th>Actions</Th>}
              </tr>
            </thead>
            <tbody>
              {terms.map((term) => (
                <tr key={term.id}>
                  <Td>
                    <span
                      className={
                        term.rule_type === "prohibited"
                          ? "rounded border border-red-brand/30 bg-red-wash px-1.5 py-0.5 text-[11px] font-medium text-red-brand"
                          : "rounded border border-teal/30 bg-teal-wash px-1.5 py-0.5 text-[11px] font-medium text-teal-dark"
                      }
                    >
                      {term.rule_type}
                    </span>
                  </Td>
                  <Td className="font-medium">{term.term}</Td>
                  <Td className="max-w-md text-ink-soft">{term.description || "—"}</Td>
                  {isAdmin && (
                    <Td>
                      <div className="flex items-center gap-1">
                        <Button size="sm" onClick={() => openEdit(term)}>
                          <Pencil className="h-3 w-3" aria-hidden /> Edit
                        </Button>
                        <Button size="sm" variant="danger" onClick={() => void handleDelete(term)}>
                          <Trash2 className="h-3 w-3" aria-hidden />
                        </Button>
                      </div>
                    </Td>
                  )}
                </tr>
              ))}
            </tbody>
          </DataTable>
        ))}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} title={editing ? "Edit rule" : "Add rule"}>
        <form onSubmit={handleSave} className="flex flex-col gap-4" noValidate>
          {formError && <ErrorNote>{formError}</ErrorNote>}
          <Field label="Rule type" htmlFor="term-type">
            <Select
              id="term-type"
              value={form.rule_type}
              onChange={(e) => setForm({ ...form, rule_type: e.target.value as TermForm["rule_type"] })}
            >
              <option value="required">Required — the term must be used</option>
              <option value="prohibited">Prohibited — the term must not appear</option>
            </Select>
          </Field>
          <Field label="Term" htmlFor="term-word">
            <Input
              id="term-word"
              value={form.term}
              onChange={(e) => setForm({ ...form, term: e.target.value })}
              placeholder="Customer"
              required
            />
          </Field>
          <Field label="Guidance" htmlFor="term-desc">
            <Textarea
              id="term-desc"
              rows={2}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Always refer to buyers of NovaCloud as customers."
            />
          </Field>
          <div className="flex justify-end gap-2 border-t border-hairline pt-4">
            <Button type="button" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={saving}>
              {editing ? "Save changes" : "Add rule"}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}

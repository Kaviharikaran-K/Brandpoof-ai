"use client";

import { useCallback, useEffect, useState } from "react";
import { CheckCheck, Pencil, Plus, Trash2 } from "lucide-react";

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
  StatusTag,
  Td,
  Textarea,
  Th,
  TableSkeleton,
} from "@/components/ui";
import { useToast } from "@/components/toast";
import { api, formatDate } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Fact } from "@/lib/types";

interface FactForm {
  fact_id: string;
  name: string;
  approved_value: string;
  description: string;
  source_ref: string;
  version: string;
  effective_date: string;
  expiry_date: string;
}

const emptyForm: FactForm = {
  fact_id: "",
  name: "",
  approved_value: "",
  description: "",
  source_ref: "",
  version: "1",
  effective_date: "",
  expiry_date: "",
};

function toForm(fact: Fact): FactForm {
  return {
    fact_id: fact.fact_id,
    name: fact.name,
    approved_value: fact.approved_value,
    description: fact.description,
    source_ref: fact.source_ref,
    version: String(fact.version),
    effective_date: fact.effective_date ?? "",
    expiry_date: fact.expiry_date ?? "",
  };
}

export default function FactsPage() {
  const { role, orgId } = useAuth();
  const toast = useToast();
  const [facts, setFacts] = useState<Fact[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Fact | null>(null);
  const [form, setForm] = useState<FactForm>(emptyForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const isAdmin = role === "admin";
  const canCreate = role === "admin" || role === "creator";

  const load = useCallback(async () => {
    if (!orgId) return;
    try {
      setFacts(await api<Fact[]>(`/api/brand/facts${statusFilter ? `?status_filter=${statusFilter}` : ""}`));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load facts");
    }
  }, [orgId, statusFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setFormError(null);
    setDialogOpen(true);
  }

  function openEdit(fact: Fact) {
    setEditing(fact);
    setForm(toForm(fact));
    setFormError(null);
    setDialogOpen(true);
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSaving(true);
    const payload: Record<string, unknown> = {
      fact_id: form.fact_id.trim(),
      name: form.name.trim(),
      approved_value: form.approved_value.trim(),
      description: form.description.trim(),
      source_ref: form.source_ref.trim(),
      version: Number(form.version) || 1,
      effective_date: form.effective_date || null,
      expiry_date: form.expiry_date || null,
    };
    try {
      if (editing) {
        await api(`/api/brand/facts/${editing.id}`, { method: "PUT", body: JSON.stringify(payload) });
        toast.success("Fact updated", "The fact is pending confirmation again.");
      } else {
        await api("/api/brand/facts", { method: "POST", body: JSON.stringify(payload) });
        toast.success("Fact added", "It stays pending until an admin confirms it.");
      }
      setDialogOpen(false);
      await load();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not save the fact");
    } finally {
      setSaving(false);
    }
  }

  async function handleConfirm(fact: Fact) {
    try {
      await api(`/api/brand/facts/${fact.id}/confirm`, { method: "POST" });
      toast.success(`Fact ${fact.fact_id} confirmed`);
      await load();
    } catch (err) {
      toast.error("Could not confirm fact", err instanceof Error ? err.message : undefined);
    }
  }

  async function handleDelete(fact: Fact) {
    if (!window.confirm(`Delete fact ${fact.fact_id} (${fact.name})? This cannot be undone.`)) return;
    try {
      await api(`/api/brand/facts/${fact.id}`, { method: "DELETE" });
      toast.success(`Fact ${fact.fact_id} deleted`);
      await load();
    } catch (err) {
      toast.error("Could not delete fact", err instanceof Error ? err.message : undefined);
    }
  }

  return (
    <div>
      <PageHeader
        title="Approved facts"
        description="The evidence base. Facts stay pending until an admin confirms them; nothing is auto-trusted."
        actions={
          canCreate ? (
            <Button variant="primary" onClick={openCreate}>
              <Plus className="h-3.5 w-3.5" aria-hidden /> Add fact
            </Button>
          ) : undefined
        }
      />

      <div className="mb-4 flex items-center gap-3">
        <label htmlFor="fact-filter" className="text-[12px] text-ink-soft">
          Status
        </label>
        <Select
          id="fact-filter"
          className="w-44"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
        </Select>
      </div>

      {error && <ErrorNote>{error}</ErrorNote>}

      {facts === null && !error && <TableSkeleton rows={5} cols={6} />}

      {facts !== null &&
        (facts.length === 0 ? (
          <EmptyState
            icon={<CheckCheck className="h-5 w-5" />}
            title="No approved facts yet"
            description={
              canCreate
                ? "Add the verified claims your copy must respect — capacities, availability, support hours."
                : "An admin or creator needs to add the verified claims for this organisation."
            }
            action={
              canCreate ? (
                <Button variant="primary" onClick={openCreate}>
                  <Plus className="h-3.5 w-3.5" aria-hidden /> Add the first fact
                </Button>
              ) : undefined
            }
          />
        ) : (
          <DataTable>
            <thead>
              <tr>
                <Th>Fact ID</Th>
                <Th>Name</Th>
                <Th>Approved value</Th>
                <Th>Version</Th>
                <Th>Effective</Th>
                <Th>Expires</Th>
                <Th>Status</Th>
                {isAdmin && <Th>Actions</Th>}
              </tr>
            </thead>
            <tbody>
              {facts.map((fact) => (
                <tr key={fact.id}>
                  <Td className="whitespace-nowrap font-mono text-[12px] text-teal-dark">{fact.fact_id}</Td>
                  <Td>
                    <span className="text-ink">{fact.name}</span>
                    {fact.description && (
                      <span className="mt-0.5 block max-w-md text-[12px] text-ink-soft">{fact.description}</span>
                    )}
                    {fact.source_ref && (
                      <span className="mt-0.5 block max-w-md text-[11px] text-ink-faint">Source: {fact.source_ref}</span>
                    )}
                  </Td>
                  <Td className="font-medium">{fact.approved_value}</Td>
                  <Td>v{fact.version}</Td>
                  <Td className="whitespace-nowrap">{formatDate(fact.effective_date)}</Td>
                  <Td className="whitespace-nowrap">{formatDate(fact.expiry_date)}</Td>
                  <Td>
                    <StatusTag status={fact.approval_status} />
                  </Td>
                  {isAdmin && (
                    <Td>
                      <div className="flex items-center gap-1">
                        {fact.approval_status !== "approved" && (
                          <Button size="sm" variant="primary" onClick={() => void handleConfirm(fact)}>
                            <CheckCheck className="h-3 w-3" aria-hidden /> Confirm
                          </Button>
                        )}
                        <Button size="sm" onClick={() => openEdit(fact)}>
                          <Pencil className="h-3 w-3" aria-hidden /> Edit
                        </Button>
                        <Button size="sm" variant="danger" onClick={() => void handleDelete(fact)}>
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

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} title={editing ? "Edit fact" : "Add fact"} wide>
        <form onSubmit={handleSave} className="grid grid-cols-2 gap-4" noValidate>
          {formError && (
            <div className="col-span-2">
              <ErrorNote>{formError}</ErrorNote>
            </div>
          )}
          <Field label="Fact ID" htmlFor="fact-id" hint="Stable code, e.g. NC-FR-004">
            <Input
              id="fact-id"
              value={form.fact_id}
              onChange={(e) => setForm({ ...form, fact_id: e.target.value })}
              placeholder="NC-FR-004"
              required
            />
          </Field>
          <Field label="Version" htmlFor="fact-version">
            <Input
              id="fact-version"
              type="number"
              min={1}
              value={form.version}
              onChange={(e) => setForm({ ...form, version: e.target.value })}
              required
            />
          </Field>
          <div className="col-span-2">
            <Field label="Name" htmlFor="fact-name" hint="What the fact is about, e.g. Maximum supported users">
              <Input
                id="fact-name"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="Maximum supported users"
                required
              />
            </Field>
          </div>
          <div className="col-span-2">
            <Field label="Approved value" htmlFor="fact-value" hint="The only value copy may state, e.g. 5,000">
              <Input
                id="fact-value"
                value={form.approved_value}
                onChange={(e) => setForm({ ...form, approved_value: e.target.value })}
                placeholder="5,000"
                required
              />
            </Field>
          </div>
          <div className="col-span-2">
            <Field label="Description" htmlFor="fact-desc">
              <Textarea
                id="fact-desc"
                rows={2}
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="NovaCloud supports up to 5,000 users per tenant."
              />
            </Field>
          </div>
          <div className="col-span-2">
            <Field label="Source reference" htmlFor="fact-source" hint="Where the value comes from, cited in findings">
              <Input
                id="fact-source"
                value={form.source_ref}
                onChange={(e) => setForm({ ...form, source_ref: e.target.value })}
                placeholder="NovaCloud Product Handbook v2.1, section 2.4"
              />
            </Field>
          </div>
          <Field label="Effective date" htmlFor="fact-effective">
            <Input
              id="fact-effective"
              type="date"
              value={form.effective_date}
              onChange={(e) => setForm({ ...form, effective_date: e.target.value })}
            />
          </Field>
          <Field label="Expiry date" htmlFor="fact-expiry">
            <Input
              id="fact-expiry"
              type="date"
              value={form.expiry_date}
              onChange={(e) => setForm({ ...form, expiry_date: e.target.value })}
            />
          </Field>
          <div className="col-span-2 mt-2 flex justify-end gap-2 border-t border-hairline pt-4">
            <Button type="button" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={saving}>
              {editing ? "Save changes" : "Add fact"}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}

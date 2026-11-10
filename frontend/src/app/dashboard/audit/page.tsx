"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { History, ShieldAlert } from "lucide-react";

import {
  DataTable,
  EmptyState,
  ErrorNote,
  Input,
  PageHeader,
  Select,
  TableSkeleton,
  Td,
  Th,
} from "@/components/ui";
import { api, formatDateTime } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { AuditEntry } from "@/lib/types";

export default function AuditPage() {
  const { role, orgId } = useAuth();
  const [entries, setEntries] = useState<AuditEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [entityFilter, setEntityFilter] = useState("");
  const [query, setQuery] = useState("");

  const load = useCallback(async () => {
    if (!orgId) return;
    if (role !== "admin" && role !== "reviewer") return;
    try {
      setEntries(await api<AuditEntry[]>("/api/audit?limit=200"));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the audit trail");
    }
  }, [orgId, role]);

  useEffect(() => {
    void load();
  }, [load]);

  const entityTypes = useMemo(() => {
    const types = new Set<string>();
    (entries ?? []).forEach((entry) => types.add(entry.entity_type));
    return Array.from(types).sort();
  }, [entries]);

  const filtered = useMemo(() => {
    if (!entries) return null;
    const needle = query.trim().toLowerCase();
    return entries.filter((entry) => {
      if (entityFilter && entry.entity_type !== entityFilter) return false;
      if (!needle) return true;
      return (
        entry.action.toLowerCase().includes(needle) ||
        (entry.user_email ?? "").toLowerCase().includes(needle) ||
        JSON.stringify(entry.details ?? {}).toLowerCase().includes(needle)
      );
    });
  }, [entries, entityFilter, query]);

  if (role !== null && role !== "admin" && role !== "reviewer") {
    return (
      <EmptyState
        icon={<ShieldAlert className="h-5 w-5" />}
        title="Audit access is restricted"
        description="Only admins and reviewers can browse the audit trail."
      />
    );
  }

  return (
    <div>
      <PageHeader
        title="Audit history"
        description="Every workflow transition is recorded. Decisions, revisions and analyses are attributable."
      />

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1">
          <label htmlFor="audit-entity" className="text-[11px] text-ink-soft">
            Entity
          </label>
          <Select
            id="audit-entity"
            className="w-56"
            value={entityFilter}
            onChange={(e) => setEntityFilter(e.target.value)}
          >
            <option value="">All entities</option>
            {entityTypes.map((type) => (
              <option key={type} value={type}>
                {type.replace(/_/g, " ")}
              </option>
            ))}
          </Select>
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="audit-query" className="text-[11px] text-ink-soft">
            Search action, user or details
          </label>
          <Input
            id="audit-query"
            className="w-72"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. submission.approve"
          />
        </div>
      </div>

      {error && <ErrorNote>{error}</ErrorNote>}
      {entries === null && !error && <TableSkeleton rows={6} cols={5} />}

      {filtered !== null && filtered.length === 0 && (
        <EmptyState
          icon={<History className="h-5 w-5" />}
          title="No matching audit entries"
          description="Adjust the filters or perform a workflow action to populate the trail."
        />
      )}

      {filtered !== null && filtered.length > 0 && (
        <DataTable>
          <thead>
            <tr>
              <Th>When</Th>
              <Th>User</Th>
              <Th>Action</Th>
              <Th>Entity</Th>
              <Th>Details</Th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((entry) => (
              <tr key={entry.id}>
                <Td className="whitespace-nowrap text-[12px] text-ink-soft">
                  {formatDateTime(entry.created_at)}
                </Td>
                <Td className="text-[12px]">{entry.user_email ?? "system"}</Td>
                <Td className="whitespace-nowrap font-mono text-[12px] text-teal-dark">{entry.action}</Td>
                <Td className="text-[12px]">
                  {entry.entity_type.replace(/_/g, " ")}
                  <span className="ml-1 text-ink-faint">#{entry.entity_id ?? "—"}</span>
                </Td>
                <Td>
                  <code className="block max-w-md break-words text-[11px] text-ink-soft">
                    {Object.keys(entry.details ?? {}).length > 0 ? JSON.stringify(entry.details) : "—"}
                  </code>
                </Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
    </div>
  );
}

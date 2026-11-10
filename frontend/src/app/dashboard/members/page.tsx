"use client";

import { useCallback, useEffect, useState } from "react";
import { Trash2, UserPlus } from "lucide-react";

import {
  Button,
  DataTable,
  Dialog,
  EmptyState,
  ErrorNote,
  Field,
  Input,
  PageHeader,
  RoleTag,
  Select,
  Td,
  Th,
  TableSkeleton,
} from "@/components/ui";
import { useToast } from "@/components/toast";
import { api, formatDateTime } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Member, Role } from "@/lib/types";

export default function MembersPage() {
  const { orgId } = useAuth();
  const toast = useToast();
  const [members, setMembers] = useState<Member[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [newRole, setNewRole] = useState<Role>("creator");
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    if (!orgId) return;
    try {
      setMembers(await api<Member[]>(`/api/organisations/${orgId}/members`));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load members");
    }
  }, [orgId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSaving(true);
    try {
      await api(`/api/organisations/${orgId}/members`, {
        method: "POST",
        body: JSON.stringify({ email: email.trim(), role: newRole }),
      });
      toast.success("Member added", `${email.trim()} is now a ${newRole}.`);
      setDialogOpen(false);
      setEmail("");
      await load();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not add member");
    } finally {
      setSaving(false);
    }
  }

  async function handleRoleChange(member: Member, role: Role) {
    try {
      await api(`/api/organisations/${orgId}/members/${member.user_id}`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
      });
      toast.success("Role updated", `${member.full_name} is now a ${role}.`);
      await load();
    } catch (err) {
      toast.error("Could not update role", err instanceof Error ? err.message : undefined);
    }
  }

  async function handleRemove(member: Member) {
    if (!window.confirm(`Remove ${member.full_name} (${member.email}) from this organisation?`)) return;
    try {
      await api(`/api/organisations/${orgId}/members/${member.user_id}`, { method: "DELETE" });
      toast.success("Member removed");
      await load();
    } catch (err) {
      toast.error("Could not remove member", err instanceof Error ? err.message : undefined);
    }
  }

  return (
    <div>
      <PageHeader
        title="Members"
        description="Roles decide what each person can do: admins manage the evidence base, creators submit content, reviewers approve it."
        actions={
          <Button variant="primary" onClick={() => setDialogOpen(true)}>
            <UserPlus className="h-3.5 w-3.5" aria-hidden /> Add member
          </Button>
        }
      />

      {error && <ErrorNote>{error}</ErrorNote>}

      {members === null && !error && <TableSkeleton rows={3} cols={4} />}

      {members !== null &&
        (members.length === 0 ? (
          <EmptyState
            icon={<UserPlus className="h-5 w-5" />}
            title="No members yet"
            description="Invite people by email once they have registered an account."
          />
        ) : (
          <DataTable>
            <thead>
              <tr>
                <Th>Name</Th>
                <Th>Email</Th>
                <Th>Role</Th>
                <Th>Joined</Th>
                <Th>Actions</Th>
              </tr>
            </thead>
            <tbody>
              {members.map((member) => (
                <tr key={member.user_id}>
                  <Td className="font-medium">{member.full_name}</Td>
                  <Td className="font-mono text-[12px] text-ink-soft">{member.email}</Td>
                  <Td>
                    <Select
                      value={member.role}
                      onChange={(e) => void handleRoleChange(member, e.target.value as Role)}
                      className="w-32"
                      aria-label={`Role for ${member.full_name}`}
                    >
                      <option value="admin">admin</option>
                      <option value="creator">creator</option>
                      <option value="reviewer">reviewer</option>
                    </Select>
                  </Td>
                  <Td className="whitespace-nowrap text-ink-soft">{formatDateTime(member.joined_at)}</Td>
                  <Td>
                    <Button size="sm" variant="danger" onClick={() => void handleRemove(member)}>
                      <Trash2 className="h-3 w-3" aria-hidden /> Remove
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        ))}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} title="Add member">
        <form onSubmit={handleAdd} className="flex flex-col gap-4" noValidate>
          {formError && <ErrorNote>{formError}</ErrorNote>}
          <Field
            label="Email"
            htmlFor="member-email"
            hint="The person must already have a BrandProof account."
          >
            <Input
              id="member-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="colleague@company.example"
              required
            />
          </Field>
          <Field label="Role" htmlFor="member-role">
            <Select
              id="member-role"
              value={newRole}
              onChange={(e) => setNewRole(e.target.value as Role)}
            >
              <option value="admin">Admin — manage facts, members and assets</option>
              <option value="creator">Creator — write and submit content</option>
              <option value="reviewer">Reviewer — approve, reject, request changes</option>
            </Select>
          </Field>
          <div className="flex justify-end gap-2 border-t border-hairline pt-4">
            <Button type="button" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={saving}>
              Add member
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}

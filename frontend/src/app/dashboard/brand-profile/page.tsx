"use client";

import { useCallback, useEffect, useState } from "react";

import { Button, Card, ErrorNote, Field, Input, PageHeader, Textarea } from "@/components/ui";
import { useToast } from "@/components/toast";
import { api, formatDateTime } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { AiConsent, BrandProfile } from "@/lib/types";

interface ProfileForm {
  name: string;
  product_name: string;
  tagline: string;
  tone: string;
  description: string;
}

const emptyForm: ProfileForm = {
  name: "",
  product_name: "",
  tagline: "",
  tone: "",
  description: "",
};

export default function BrandProfilePage() {
  const { role, orgId } = useAuth();
  const toast = useToast();
  const [form, setForm] = useState<ProfileForm>(emptyForm);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [consent, setConsent] = useState<AiConsent | null>(null);
  const [savingConsent, setSavingConsent] = useState(false);

  const isAdmin = role === "admin";

  const load = useCallback(async () => {
    if (!orgId) return;
    try {
      const [profile, aiConsent] = await Promise.all([
        api<BrandProfile | null>("/api/brand/profile"),
        api<AiConsent>("/api/settings/ai-consent"),
      ]);
      if (profile) {
        setForm({
          name: profile.name,
          product_name: profile.product_name,
          tagline: profile.tagline,
          tone: profile.tone,
          description: profile.description,
        });
      }
      setConsent(aiConsent);
      setLoaded(true);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load brand profile");
    }
  }, [orgId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await api("/api/brand/profile", { method: "PUT", body: JSON.stringify(form) });
      toast.success("Brand profile saved");
    } catch (err) {
      toast.error("Could not save profile", err instanceof Error ? err.message : undefined);
    } finally {
      setSaving(false);
    }
  }

  async function toggleConsent() {
    if (!consent) return;
    setSavingConsent(true);
    try {
      const updated = await api<AiConsent>("/api/settings/ai-consent", {
        method: "PATCH",
        body: JSON.stringify({ consent: !consent.consent }),
      });
      setConsent(updated);
      toast.success(
        updated.consent ? "External AI language review enabled" : "External AI language review disabled"
      );
    } catch (err) {
      toast.error("Could not update AI consent", err instanceof Error ? err.message : undefined);
    } finally {
      setSavingConsent(false);
    }
  }

  if (error) {
    return (
      <div>
        <PageHeader title="Brand profile" description="The identity this organisation governs." />
        <ErrorNote>{error}</ErrorNote>
      </div>
    );
  }

  if (!loaded) {
    return (
      <div>
        <PageHeader title="Brand profile" description="The identity this organisation governs." />
        <div className="skeleton h-64 w-full max-w-2xl" />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Brand profile"
        description="The identity this organisation governs. Admins can edit; everyone can read."
      />
      <form
        onSubmit={handleSave}
        className="grid max-w-2xl grid-cols-1 gap-4 rounded border border-hairline bg-white p-6 sm:grid-cols-2"
        noValidate
      >
        <Field label="Brand name" htmlFor="bp-name">
          <Input
            id="bp-name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="NovaTech Solutions"
            disabled={!isAdmin}
          />
        </Field>
        <Field label="Product name" htmlFor="bp-product">
          <Input
            id="bp-product"
            value={form.product_name}
            onChange={(e) => setForm({ ...form, product_name: e.target.value })}
            placeholder="NovaCloud"
            disabled={!isAdmin}
          />
        </Field>
        <div className="sm:col-span-2">
          <Field label="Tagline" htmlFor="bp-tagline">
            <Input
              id="bp-tagline"
              value={form.tagline}
              onChange={(e) => setForm({ ...form, tagline: e.target.value })}
              placeholder="Dependable cloud, plainly explained."
              disabled={!isAdmin}
            />
          </Field>
        </div>
        <div className="sm:col-span-2">
          <Field label="Tone of voice" htmlFor="bp-tone">
            <Input
              id="bp-tone"
              value={form.tone}
              onChange={(e) => setForm({ ...form, tone: e.target.value })}
              placeholder="Professional and friendly"
              disabled={!isAdmin}
            />
          </Field>
        </div>
        <div className="sm:col-span-2">
          <Field label="Description" htmlFor="bp-desc">
            <Textarea
              id="bp-desc"
              rows={4}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="What the brand stands for, who it serves."
              disabled={!isAdmin}
            />
          </Field>
        </div>
        {isAdmin && (
          <div className="sm:col-span-2 flex justify-end border-t border-hairline pt-4">
            <Button type="submit" variant="primary" loading={saving}>
              Save profile
            </Button>
          </div>
        )}
      </form>

      {consent && (
        <Card className="mt-4 max-w-2xl p-5">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h2 className="font-serif text-[18px] text-ink">External AI analysis</h2>
              <p className="mt-1 text-[12px] text-ink-soft">
                Deterministic checks (facts, terminology, palettes, contrast) always run inside
                BrandProof. Optional tone and language review can send submitted copy to an external
                AI provider — only when an admin consents below.
              </p>
            </div>
            <span
              className={
                consent.consent
                  ? "rounded border border-teal/30 bg-teal-wash px-1.5 py-0.5 text-[11px] font-medium text-teal-dark"
                  : "rounded border border-hairline bg-paper px-1.5 py-0.5 text-[11px] font-medium text-ink-soft"
              }
            >
              {consent.consent ? "Enabled" : "Disabled"}
            </span>
          </div>

          <blockquote className="mt-3 rounded border border-hairline bg-paper px-3 py-2 text-[11px] text-ink-soft">
            {consent.disclosure}
          </blockquote>

          <p className="mt-2 text-[11px] text-ink-faint">
            Provider: {consent.provider_configured ? "configured" : "not configured"} · {consent.note}
          </p>
          <p className="mt-1 text-[11px] text-ink-faint">
            Last updated {formatDateTime(consent.updated_at)}
          </p>

          {isAdmin && (
            <div className="mt-3 flex justify-end border-t border-hairline pt-3">
              <Button
                type="button"
                variant={consent.consent ? "secondary" : "primary"}
                onClick={toggleConsent}
                loading={savingConsent}
              >
                {consent.consent ? "Disable external AI review" : "Enable external AI review"}
              </Button>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

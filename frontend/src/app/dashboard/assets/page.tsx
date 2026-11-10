"use client";

import { useCallback, useEffect, useState } from "react";
import { Palette, Trash2, Upload } from "lucide-react";

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
import { api, formatDateTime } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Asset } from "@/lib/types";

export default function AssetsPage() {
  const { role, orgId } = useAuth();
  const toast = useToast();
  const [assets, setAssets] = useState<Asset[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [colourName, setColourName] = useState("");
  const [colourValue, setColourValue] = useState("#");
  const [logoName, setLogoName] = useState("");
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [savingColour, setSavingColour] = useState(false);
  const [savingLogo, setSavingLogo] = useState(false);

  const isAdmin = role === "admin";

  const load = useCallback(async () => {
    if (!orgId) return;
    try {
      setAssets(await api<Asset[]>("/api/brand/assets"));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load assets");
    }
  }, [orgId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleAddColour(e: React.FormEvent) {
    e.preventDefault();
    if (!/^#[0-9A-Fa-f]{6}$/.test(colourValue)) {
      toast.error("Colour must be a 6-digit hex value like #0F766E");
      return;
    }
    setSavingColour(true);
    try {
      await api("/api/brand/assets/colours", {
        method: "POST",
        body: JSON.stringify({ name: colourName.trim(), colour_value: colourValue }),
      });
      toast.success("Colour added");
      setColourName("");
      setColourValue("#");
      await load();
    } catch (err) {
      toast.error("Could not add colour", err instanceof Error ? err.message : undefined);
    } finally {
      setSavingColour(false);
    }
  }

  async function handleUploadLogo(e: React.FormEvent) {
    e.preventDefault();
    if (!logoFile) {
      toast.error("Choose a logo file first");
      return;
    }
    setSavingLogo(true);
    try {
      const data = new FormData();
      data.set("name", logoName.trim() || logoFile.name);
      data.set("file", logoFile);
      await api("/api/brand/assets/logos", { method: "POST", body: data });
      toast.success("Logo uploaded");
      setLogoName("");
      setLogoFile(null);
      await load();
    } catch (err) {
      toast.error("Upload failed", err instanceof Error ? err.message : undefined);
    } finally {
      setSavingLogo(false);
    }
  }

  async function handleDelete(asset: Asset) {
    if (!window.confirm(`Delete ${asset.asset_type} "${asset.name}"?`)) return;
    try {
      await api(`/api/brand/assets/${asset.id}`, { method: "DELETE" });
      toast.success("Asset deleted");
      await load();
    } catch (err) {
      toast.error("Could not delete asset", err instanceof Error ? err.message : undefined);
    }
  }

  const colours = assets?.filter((a) => a.asset_type === "colour") ?? [];
  const logos = assets?.filter((a) => a.asset_type === "logo") ?? [];

  return (
    <div>
      <PageHeader
        title="Brand assets"
        description="Approved logos and colour palette, used by checks and the visual inspector."
      />

      {error && <ErrorNote>{error}</ErrorNote>}

      <h2 className="mb-3 font-serif text-[17px] text-ink">Colour palette</h2>

      {isAdmin && (
        <form
          onSubmit={handleAddColour}
          className="mb-4 flex flex-wrap items-end gap-3 rounded border border-hairline bg-white p-4"
          noValidate
        >
          <div className="w-48">
            <Field label="Name" htmlFor="colour-name">
              <Input
                id="colour-name"
                value={colourName}
                onChange={(e) => setColourName(e.target.value)}
                placeholder="Nova Teal"
                required
              />
            </Field>
          </div>
          <div className="w-36">
            <Field label="Hex value" htmlFor="colour-value">
              <div className="flex items-center gap-2">
                <span
                  className="h-8 w-8 shrink-0 rounded border border-hairline"
                  style={{ backgroundColor: /^#[0-9A-Fa-f]{6}$/.test(colourValue) ? colourValue : "#FFFFFF" }}
                  aria-hidden
                />
                <Input
                  id="colour-value"
                  value={colourValue}
                  onChange={(e) => setColourValue(e.target.value)}
                  placeholder="#0F766E"
                  className="font-mono"
                  required
                />
              </div>
            </Field>
          </div>
          <Button type="submit" variant="primary" loading={savingColour}>
            Add colour
          </Button>
        </form>
      )}

      {assets === null && !error && <TableSkeleton rows={3} cols={3} />}

      {assets !== null &&
        (colours.length === 0 ? (
          <EmptyState
            icon={<Palette className="h-5 w-5" />}
            title="No approved colours yet"
            description="Add the brand palette as hex values."
          />
        ) : (
          <DataTable>
            <thead>
              <tr>
                <Th>Swatch</Th>
                <Th>Name</Th>
                <Th>Hex</Th>
                <Th>Added</Th>
                {isAdmin && <Th>Actions</Th>}
              </tr>
            </thead>
            <tbody>
              {colours.map((asset) => (
                <tr key={asset.id}>
                  <Td>
                    <span
                      className="inline-block h-5 w-5 rounded border border-hairline"
                      style={{ backgroundColor: asset.colour_value ?? "#FFFFFF" }}
                      aria-label={`Swatch for ${asset.name}`}
                    />
                  </Td>
                  <Td className="font-medium">{asset.name}</Td>
                  <Td className="font-mono text-[12px]">{asset.colour_value}</Td>
                  <Td className="whitespace-nowrap text-ink-soft">{formatDateTime(asset.created_at)}</Td>
                  {isAdmin && (
                    <Td>
                      <Button size="sm" variant="danger" onClick={() => void handleDelete(asset)}>
                        <Trash2 className="h-3 w-3" aria-hidden />
                      </Button>
                    </Td>
                  )}
                </tr>
              ))}
            </tbody>
          </DataTable>
        ))}

      <h2 className="mb-3 mt-8 font-serif text-[17px] text-ink">Logos</h2>

      {isAdmin && (
        <form
          onSubmit={handleUploadLogo}
          className="mb-4 flex flex-wrap items-end gap-3 rounded border border-hairline bg-white p-4"
          noValidate
        >
          <div className="w-48">
            <Field label="Name" htmlFor="logo-name">
              <Input
                id="logo-name"
                value={logoName}
                onChange={(e) => setLogoName(e.target.value)}
                placeholder="Primary logo"
                required
              />
            </Field>
          </div>
          <div className="flex-1">
            <Field label="File" htmlFor="logo-file" hint="PNG, JPG, SVG or WebP (max 10 MB)">
              <input
                id="logo-file"
                type="file"
                accept=".png,.jpg,.jpeg,.svg,.webp"
                onChange={(e) => setLogoFile(e.target.files?.[0] ?? null)}
                className="w-full rounded border border-hairline bg-white px-2.5 py-1.5 text-[12px] text-ink file:mr-3 file:rounded file:border-0 file:bg-paper file:px-2 file:py-1 file:text-[12px] file:text-ink-soft"
              />
            </Field>
          </div>
          <Button type="submit" variant="primary" loading={savingLogo}>
            <Upload className="h-3.5 w-3.5" aria-hidden /> Upload logo
          </Button>
        </form>
      )}

      {assets !== null &&
        (logos.length === 0 ? (
          <EmptyState
            icon={<Palette className="h-5 w-5" />}
            title="No logos uploaded yet"
            description="Upload the approved logo files for this organisation."
          />
        ) : (
          <DataTable>
            <thead>
              <tr>
                <Th>Preview</Th>
                <Th>Name</Th>
                <Th>File</Th>
                <Th>Added</Th>
                {isAdmin && <Th>Actions</Th>}
              </tr>
            </thead>
            <tbody>
              {logos.map((asset) => (
                <tr key={asset.id}>
                  <Td>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={`/api/brand/assets/logos/${asset.id}/file`}
                      alt={`${asset.name} preview`}
                      className="h-8 max-w-[120px] rounded border border-hairline bg-paper object-contain p-1"
                    />
                  </Td>
                  <Td className="font-medium">{asset.name}</Td>
                  <Td className="max-w-xs truncate font-mono text-[12px] text-ink-soft">{asset.file_name}</Td>
                  <Td className="whitespace-nowrap text-ink-soft">{formatDateTime(asset.created_at)}</Td>
                  {isAdmin && (
                    <Td>
                      <Button size="sm" variant="danger" onClick={() => void handleDelete(asset)}>
                        <Trash2 className="h-3 w-3" aria-hidden />
                      </Button>
                    </Td>
                  )}
                </tr>
              ))}
            </tbody>
          </DataTable>
        ))}
    </div>
  );
}

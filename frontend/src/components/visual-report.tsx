"use client";

import { AlertTriangle, CheckCircle2, ScanSearch, XCircle } from "lucide-react";

import { cx } from "@/components/ui";
import type { VisualReport } from "@/lib/types";

const VERDICT_STYLES: Record<string, string> = {
  match: "border-teal/40 bg-teal-wash text-teal-dark",
  close: "border-amber-brand/40 bg-amber-wash text-amber-brand",
  deviation: "border-red-brand/40 bg-red-wash text-red-brand",
};

function Swatch({ hex }: { hex: string }) {
  return (
    <span
      className="inline-block h-4 w-4 shrink-0 rounded-sm border border-ink/10"
      style={{ backgroundColor: hex }}
      aria-hidden
    />
  );
}

function Capability({ label, on }: { label: string; on: boolean }) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-medium",
        on
          ? "border-teal/30 bg-teal-wash text-teal-dark"
          : "border-hairline bg-paper text-ink-faint"
      )}
    >
      {label}: {on ? "on" : "off"}
    </span>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-ink-faint">{children}</p>
  );
}

export function VisualReportPanel({ report }: { report: VisualReport }) {
  const { capabilities: caps, dominant_colours: dominant, palette_matches: matches, contrast, logo } =
    report;

  return (
    <div className="mt-3 rounded border border-hairline bg-paper/70 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <ScanSearch className="h-3.5 w-3.5 text-teal" aria-hidden />
        <p className="text-[12px] font-semibold text-ink">Visual inspection</p>
        {!report.available && (
          <span className="rounded border border-amber-brand/40 bg-amber-wash px-1.5 py-0.5 text-[10px] font-medium text-amber-brand">
            Requires human review
          </span>
        )}
        <span className="ml-auto font-mono text-[10px] text-ink-faint">
          {report.image.width && report.image.height
            ? `${report.image.width}×${report.image.height}${report.image.format ? ` · ${report.image.format}` : ""}`
            : "measurements"}
        </span>
      </div>

      <div className="mt-2 flex flex-wrap gap-1.5">
        <Capability label="Pixels" on={caps.pixel_analysis} />
        <Capability label="OCR" on={caps.ocr} />
        <Capability label="Logo match" on={caps.logo_match} />
        <Capability label="Palette" on={caps.palette_configured} />
      </div>

      {dominant.length > 0 && (
        <div className="mt-3">
          <SectionLabel>Dominant colours</SectionLabel>
          <div className="flex flex-wrap gap-1.5">
            {dominant.map((colour) => (
              <span
                key={colour.hex}
                className="inline-flex items-center gap-1.5 rounded border border-hairline bg-white px-1.5 py-0.5 text-[10px] text-ink-soft"
              >
                <Swatch hex={colour.hex} />
                <span className="font-mono">{colour.hex}</span>
                <span>{Math.round(colour.share * 100)}%</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {matches.length > 0 && (
        <div className="mt-3">
          <SectionLabel>Palette deviation (CIE76 ΔE, lower is closer)</SectionLabel>
          <ul className="space-y-1">
            {matches.map((match) => (
              <li
                key={`${match.hex}-${match.nearest_hex}`}
                className="flex flex-wrap items-center gap-1.5 text-[11px] text-ink-soft"
              >
                <Swatch hex={match.hex} />
                <span className="font-mono">{match.hex}</span>
                <span>{Math.round(match.share * 100)}%</span>
                <span className="text-ink-faint">→</span>
                <Swatch hex={match.nearest_hex} />
                <span>{match.nearest_name}</span>
                <span className="font-mono text-ink-faint">ΔE {match.delta_e.toFixed(1)}</span>
                <span
                  className={cx(
                    "rounded border px-1 py-0.5 text-[10px] font-medium",
                    VERDICT_STYLES[match.verdict] ?? VERDICT_STYLES.deviation
                  )}
                >
                  {match.verdict}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {contrast.length > 0 && (
        <div className="mt-3">
          <SectionLabel>Contrast (WCAG)</SectionLabel>
          <ul className="space-y-1">
            {contrast.map((pair) => (
              <li
                key={`${pair.foreground}-${pair.background}`}
                className="flex flex-wrap items-center gap-1.5 text-[11px] text-ink-soft"
              >
                <Swatch hex={pair.foreground} />
                <span className="font-mono">{pair.foreground}</span>
                <span className="text-ink-faint">on</span>
                <Swatch hex={pair.background} />
                <span className="font-mono">{pair.background}</span>
                <span className="font-mono text-ink-faint">{pair.ratio.toFixed(2)}:1</span>
                <span className="inline-flex items-center gap-0.5 text-[10px]">
                  {pair.wcag_aa_normal ? (
                    <CheckCircle2 className="h-3 w-3 text-teal" aria-hidden />
                  ) : (
                    <XCircle className="h-3 w-3 text-red-brand" aria-hidden />
                  )}
                  AA
                </span>
                <span className="inline-flex items-center gap-0.5 text-[10px]">
                  {pair.wcag_aa_large ? (
                    <CheckCircle2 className="h-3 w-3 text-teal" aria-hidden />
                  ) : (
                    <XCircle className="h-3 w-3 text-red-brand" aria-hidden />
                  )}
                  AA large
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-3">
        <SectionLabel>Logo match</SectionLabel>
        {logo.checked ? (
          <p className="text-[11px] text-ink-soft">
            {logo.matched ? (
              <>
                Approved logo detected · score{" "}
                <span className="font-mono text-teal-dark">{logo.best_score?.toFixed(2)}</span>
                {logo.threshold !== undefined && (
                  <span className="text-ink-faint"> (threshold {logo.threshold.toFixed(2)})</span>
                )}
              </>
            ) : (
              <>
                Approved logo not confidently detected · best score{" "}
                <span className="font-mono">{logo.best_score?.toFixed(2) ?? "—"}</span>
                {logo.threshold !== undefined && (
                  <span className="text-ink-faint"> (threshold {logo.threshold.toFixed(2)})</span>
                )}
              </>
            )}
          </p>
        ) : (
          <p className="text-[11px] text-ink-faint">
            No approved logo asset configured, or the format could not be compared.
          </p>
        )}
      </div>

      {report.limitations.length > 0 && (
        <div className="mt-3 rounded border border-amber-brand/30 bg-amber-wash/60 px-2 py-1.5">
          <p className="mb-1 flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-amber-brand">
            <AlertTriangle className="h-3 w-3" aria-hidden /> Limitations
          </p>
          <ul className="list-disc space-y-0.5 pl-4 text-[11px] text-ink-soft">
            {report.limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
        </div>
      )}

      {report.note && <p className="mt-2 text-[11px] italic text-ink-faint">{report.note}</p>}
    </div>
  );
}

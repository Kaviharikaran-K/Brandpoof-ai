"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { BarChart3, ClipboardList, Clock3 } from "lucide-react";

import {
  Card,
  EmptyState,
  ErrorNote,
  PageHeader,
  Select,
  TableSkeleton,
} from "@/components/ui";
import { SeverityTag } from "@/components/findings";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type {
  AnalyticsIssues,
  AnalyticsOverview,
  AnalyticsTrends,
  RepeatedIssue,
  Severity,
} from "@/lib/types";

const RANGES = [
  { value: "7", label: "Last 7 days" },
  { value: "30", label: "Last 30 days" },
  { value: "90", label: "Last 90 days" },
  { value: "365", label: "Last 12 months" },
  { value: "all", label: "All time" },
];

const TEAL = "#0F766E";
const INK = "#14213D";
const AMBER = "#B54708";
const RED = "#B4232A";
const HAIRLINE = "#E4E0D5";

const TOOLTIP_STYLE = {
  background: "#ffffff",
  border: `1px solid ${HAIRLINE}`,
  borderRadius: 4,
  fontSize: 12,
  color: INK,
};

function isoDate(offsetDays: number): string {
  const date = new Date();
  date.setDate(date.getDate() - offsetDays);
  return date.toISOString().slice(0, 10);
}

function shortDate(value: string): string {
  const date = new Date(`${value}T00:00:00`);
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

function Kpi({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Card className="p-3">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-faint">{label}</p>
      <p className="mt-1 font-serif text-[24px] leading-none text-ink">{value}</p>
      {hint && <p className="mt-1 text-[11px] text-ink-faint">{hint}</p>}
    </Card>
  );
}

function IssueTable({
  title,
  rows,
  empty,
}: {
  title: string;
  rows: RepeatedIssue[];
  empty: string;
}) {
  return (
    <Card className="p-4">
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-ink-faint">{title}</p>
      {rows.length === 0 ? (
        <p className="text-[12px] text-ink-faint">{empty}</p>
      ) : (
        <ul className="space-y-1.5">
          {rows.map((row) => (
            <li key={`${row.category}-${row.detected_text}`} className="flex items-start gap-2 text-[12px]">
              <span className="mt-0.5 inline-flex min-w-6 justify-center rounded border border-hairline bg-paper px-1 font-mono text-[11px] text-ink-soft">
                {row.count}
              </span>
              <span className="min-w-0">
                <span className="block truncate font-mono text-[11px] text-ink">“{row.detected_text}”</span>
                <span className="text-[11px] text-ink-faint">{row.category}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export default function AnalyticsPage() {
  const { orgId, loading: authLoading } = useAuth();
  const [range, setRange] = useState("30");
  const [category, setCategory] = useState("");
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [issues, setIssues] = useState<AnalyticsIssues | null>(null);
  const [trends, setTrends] = useState<AnalyticsTrends | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!orgId) return;
    setLoading(true);
    try {
      const query = new URLSearchParams();
      if (range !== "all") {
        query.set("date_from", isoDate(Number(range) - 1));
        query.set("date_to", isoDate(0));
      }
      const trendQuery = new URLSearchParams(query);
      if (range !== "all") trendQuery.set("days", range);
      if (category) {
        query.set("category", category);
        trendQuery.set("category", category);
      }
      const [overviewData, issuesData, trendsData] = await Promise.all([
        api<AnalyticsOverview>(`/api/analytics/overview?${query.toString()}`),
        api<AnalyticsIssues>(`/api/analytics/issues?${query.toString()}`),
        api<AnalyticsTrends>(`/api/analytics/trends?${trendQuery.toString()}`),
      ]);
      setOverview(overviewData);
      setIssues(issuesData);
      setTrends(trendsData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load analytics");
    } finally {
      setLoading(false);
    }
  }, [orgId, range, category]);

  useEffect(() => {
    if (authLoading) return;
    void load();
  }, [authLoading, load]);

  const categories = overview?.categories ?? [];
  const severityCounts = issues?.severities ?? [];
  const overallFindings = severityCounts.reduce((sum, item) => sum + item.count, 0);

  const trendData = useMemo(
    () =>
      (trends?.series ?? []).map((point) => ({
        ...point,
        label: shortDate(point.date),
      })),
    [trends]
  );

  const categoryData = useMemo(
    () => (issues?.categories ?? []).map((item) => ({ ...item, label: item.category })),
    [issues]
  );

  const categoryTrend = useMemo(() => {
    if (!category || !trends) return [];
    return trends.by_category
      .filter((point) => point.category === category)
      .map((point) => ({ ...point, label: shortDate(point.date) }));
  }, [category, trends]);

  const trendAxis = trendData.length > 60 ? 12 : trendData.length > 30 ? 6 : 3;

  return (
    <div>
      <PageHeader
        title="Analytics"
        description="Every number is derived from stored submissions, analysis runs and human decisions. No analytics provider, no sampled estimates."
        actions={
          <div className="flex items-center gap-2">
            <Select
              aria-label="Date range"
              value={range}
              onChange={(e) => setRange(e.target.value)}
              className="w-auto"
            >
              {RANGES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
            <Select
              aria-label="Finding category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-auto"
            >
              <option value="">All categories</option>
              {categories.map((item) => (
                <option key={item.category} value={item.category}>
                  {item.category}
                </option>
              ))}
            </Select>
          </div>
        }
      />

      {error && <ErrorNote>{error}</ErrorNote>}

      {loading && !overview ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="skeleton h-20" />
            ))}
          </div>
          <TableSkeleton rows={4} cols={3} />
        </div>
      ) : !overview ? null : overview.totals.submissions_total === 0 ? (
        <EmptyState
          icon={<BarChart3 className="h-5 w-5 text-teal" aria-hidden />}
          title="Nothing measured in this period"
          description="Create and analyse a submission, or widen the date range. Analytics appear as soon as stored evidence exists."
        />
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <Kpi
              label="Submissions"
              value={String(overview.totals.submissions_total)}
              hint={`${overview.totals.submissions_draft} draft`}
            />
            <Kpi
              label="Approved"
              value={String(overview.totals.submissions_approved)}
              hint={`${overview.totals.submissions_rejected} rejected`}
            />
            <Kpi
              label="Awaiting review"
              value={String(overview.totals.submissions_pending)}
              hint="Human queue"
            />
            <Kpi
              label="Findings (latest)"
              value={String(overview.totals.findings_latest)}
              hint={`${overview.totals.findings_total} across all runs`}
            />
            <Kpi
              label="Needs human"
              value={String(overview.totals.needs_human_review)}
              hint={`${overview.totals.clarification_findings} clarification`}
            />
            <Kpi
              label="Avg review time"
              value={
                overview.totals.avg_review_hours === null
                  ? "—"
                  : `${overview.totals.avg_review_hours.toFixed(1)}h`
              }
              hint={
                overview.totals.avg_revision_cycles === null
                  ? "No decisions yet"
                  : `${overview.totals.avg_revision_cycles.toFixed(1)} revisions avg`
              }
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-5">
            <Card className="p-4 lg:col-span-3">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-faint">
                    Activity trend
                  </p>
                  <p className="text-[11px] text-ink-faint">
                    Submissions, findings and human decisions per day
                  </p>
                </div>
                <div className="flex items-center gap-3 text-[10px] text-ink-soft">
                  <span className="inline-flex items-center gap-1">
                    <span className="h-2 w-2 rounded-sm" style={{ background: INK }} /> Submissions
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <span className="h-2 w-2 rounded-sm" style={{ background: TEAL }} /> Findings
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <span className="h-2 w-2 rounded-sm" style={{ background: AMBER }} /> Decisions
                  </span>
                </div>
              </div>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={trendData} margin={{ top: 4, right: 8, bottom: 0, left: -18 }}>
                    <CartesianGrid stroke={HAIRLINE} strokeDasharray="2 4" vertical={false} />
                    <XAxis
                      dataKey="label"
                      tick={{ fontSize: 10, fill: "#5B6478" }}
                      axisLine={{ stroke: HAIRLINE }}
                      tickLine={false}
                      interval={trendAxis}
                    />
                    <YAxis
                      tick={{ fontSize: 10, fill: "#5B6478" }}
                      axisLine={false}
                      tickLine={false}
                      allowDecimals={false}
                    />
                    <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ fontSize: 11 }} />
                    <Area
                      type="monotone"
                      dataKey="findings"
                      name="Findings"
                      stroke={TEAL}
                      fill={TEAL}
                      fillOpacity={0.12}
                      strokeWidth={1.5}
                    />
                    <Line
                      type="monotone"
                      dataKey="submissions"
                      name="Submissions"
                      stroke={INK}
                      strokeWidth={1.5}
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="decisions"
                      name="Decisions"
                      stroke={AMBER}
                      strokeWidth={1.5}
                      strokeDasharray="4 3"
                      dot={false}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card className="p-4 lg:col-span-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-faint">
                Severity mix
              </p>
              <p className="mb-3 text-[11px] text-ink-faint">
                {overallFindings} finding{overallFindings === 1 ? "" : "s"} in the latest runs
              </p>
              <ul className="space-y-2">
                {(["Critical", "Major", "Minor", "Information"] as Severity[]).map((severity) => {
                  const count = severityCounts.find((item) => item.severity === severity)?.count ?? 0;
                  const share = overallFindings === 0 ? 0 : count / overallFindings;
                  const colour =
                    severity === "Critical"
                      ? RED
                      : severity === "Major"
                        ? AMBER
                        : severity === "Minor"
                          ? TEAL
                          : "#8A93A6";
                  return (
                    <li key={severity}>
                      <div className="mb-1 flex items-center justify-between text-[11px]">
                        <SeverityTag severity={severity} />
                        <span className="font-mono text-ink-soft">{count}</span>
                      </div>
                      <div className="h-1.5 overflow-hidden rounded bg-paper">
                        <div
                          className="h-full rounded"
                          style={{ width: `${Math.round(share * 100)}%`, background: colour }}
                        />
                      </div>
                    </li>
                  );
                })}
              </ul>
              <p className="mt-4 flex items-start gap-1.5 rounded border border-hairline bg-paper px-2 py-1.5 text-[11px] text-ink-soft">
                <ClipboardList className="mt-0.5 h-3 w-3 shrink-0 text-teal" aria-hidden />
                {overview.totals.decided_total} human decision
                {overview.totals.decided_total === 1 ? "" : "s"} recorded. Automated findings never
                approve content.
              </p>
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-5">
            <Card className="p-4 lg:col-span-3">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-faint">
                Findings by category
              </p>
              <p className="mb-2 text-[11px] text-ink-faint">
                {category ? `Filtered to ${category}` : "All categories in the latest runs"}
              </p>
              {categoryData.length === 0 ? (
                <p className="text-[12px] text-ink-faint">No findings for this filter.</p>
              ) : (
                <div style={{ height: Math.max(180, categoryData.length * 30 + 20) }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={categoryData}
                      layout="vertical"
                      margin={{ top: 0, right: 12, bottom: 0, left: 8 }}
                    >
                      <CartesianGrid stroke={HAIRLINE} strokeDasharray="2 4" horizontal={false} />
                      <XAxis
                        type="number"
                        tick={{ fontSize: 10, fill: "#5B6478" }}
                        axisLine={false}
                        tickLine={false}
                        allowDecimals={false}
                      />
                      <YAxis
                        type="category"
                        dataKey="label"
                        width={150}
                        tick={{ fontSize: 10, fill: "#14213D" }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ fontSize: 11 }} />
                      <Bar dataKey="count" name="Findings" fill={TEAL} radius={[0, 3, 3, 0]} barSize={14} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>

            <Card className="p-4 lg:col-span-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-faint">
                Status breakdown
              </p>
              <ul className="mt-2 space-y-1.5">
                {overview.status_counts.map((item) => {
                  const total = overview.totals.submissions_total || 1;
                  return (
                    <li key={item.status} className="flex items-center gap-2 text-[12px]">
                      <span className="w-40 shrink-0 text-ink-soft">{item.status}</span>
                      <span className="h-1.5 flex-1 overflow-hidden rounded bg-paper">
                        <span
                          className="block h-full rounded"
                          style={{
                            width: `${Math.round((item.count / total) * 100)}%`,
                            background: item.status === "Approved" ? TEAL : INK,
                          }}
                        />
                      </span>
                      <span className="w-6 text-right font-mono text-[11px] text-ink-soft">
                        {item.count}
                      </span>
                    </li>
                  );
                })}
              </ul>
              <p className="mt-4 flex items-center gap-1.5 text-[11px] text-ink-faint">
                <Clock3 className="h-3 w-3" aria-hidden />
                Range: {overview.date_from ?? "all time"} → {overview.date_to ?? "today"}
              </p>
            </Card>
          </div>

          {categoryTrend.length > 0 && (
            <Card className="p-4">
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-ink-faint">
                {category} over time
              </p>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={categoryTrend} margin={{ top: 4, right: 8, bottom: 0, left: -18 }}>
                    <CartesianGrid stroke={HAIRLINE} strokeDasharray="2 4" vertical={false} />
                    <XAxis
                      dataKey="label"
                      tick={{ fontSize: 10, fill: "#5B6478" }}
                      axisLine={{ stroke: HAIRLINE }}
                      tickLine={false}
                      interval={trendAxis}
                    />
                    <YAxis
                      tick={{ fontSize: 10, fill: "#5B6478" }}
                      axisLine={false}
                      tickLine={false}
                      allowDecimals={false}
                    />
                    <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ fontSize: 11 }} />
                    <Area
                      type="monotone"
                      dataKey="count"
                      name="Findings"
                      stroke={TEAL}
                      fill={TEAL}
                      fillOpacity={0.12}
                      strokeWidth={1.5}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}

          <div className="grid gap-4 lg:grid-cols-3">
            <IssueTable
              title="Repeated terminology"
              rows={issues?.repeated_terminology ?? []}
              empty="No repeated terminology findings."
            />
            <IssueTable
              title="Top factual mismatches"
              rows={issues?.top_factual_mismatches ?? []}
              empty="No factual mismatches in this period."
            />
            <IssueTable
              title="Claims routed to humans"
              rows={issues?.top_clarification_claims ?? []}
              empty="No clarification findings."
            />
          </div>
        </div>
      )}
    </div>
  );
}

"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import {
  BarChart3,
  BookText,
  CaseSensitive,
  CheckCheck,
  FileStack,
  FileText,
  History,
  LayoutList,
  ListChecks,
  LogOut,
  Palette,
  Users,
} from "lucide-react";

import { RoleTag, cx } from "@/components/ui";
import { useAuth } from "@/lib/auth-context";
import type { Role } from "@/lib/types";

const NAV: { href: string; label: string; icon: React.ComponentType<{ className?: string }>; roles: Role[] }[] = [
  { href: "/dashboard", label: "Overview", icon: LayoutList, roles: ["admin", "creator", "reviewer"] },
  { href: "/dashboard/submissions", label: "Submissions", icon: FileStack, roles: ["admin", "creator", "reviewer"] },
  { href: "/dashboard/reviews", label: "Review queue", icon: ListChecks, roles: ["admin", "reviewer"] },
  { href: "/dashboard/analytics", label: "Analytics", icon: BarChart3, roles: ["admin", "creator", "reviewer"] },
  { href: "/dashboard/brand-profile", label: "Brand profile", icon: BookText, roles: ["admin", "creator", "reviewer"] },
  { href: "/dashboard/facts", label: "Approved facts", icon: CheckCheck, roles: ["admin", "creator", "reviewer"] },
  { href: "/dashboard/terminology", label: "Terminology", icon: CaseSensitive, roles: ["admin", "creator", "reviewer"] },
  { href: "/dashboard/guidelines", label: "Guidelines", icon: FileText, roles: ["admin", "creator", "reviewer"] },
  { href: "/dashboard/assets", label: "Brand assets", icon: Palette, roles: ["admin", "creator", "reviewer"] },
  { href: "/dashboard/members", label: "Members", icon: Users, roles: ["admin"] },
  { href: "/dashboard/audit", label: "Audit history", icon: History, roles: ["admin", "reviewer"] },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/dashboard") return pathname === href;
  return pathname === href || pathname.startsWith(`${href}/`);
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { me, loading, role, orgId, setOrgId, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !me) {
      router.replace("/login");
    }
  }, [loading, me, router]);

  if (loading) {
    return (
      <div className="flex min-h-screen">
        <div className="hidden w-56 shrink-0 border-r border-hairline bg-paper md:block">
          <div className="space-y-3 p-4">
            <div className="skeleton h-6 w-28" />
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="skeleton h-5 w-full" />
            ))}
          </div>
        </div>
        <div className="flex-1 p-8">
          <div className="skeleton h-8 w-64" />
          <div className="mt-6 space-y-3">
            <div className="skeleton h-4 w-full max-w-xl" />
            <div className="skeleton h-4 w-full max-w-md" />
          </div>
        </div>
      </div>
    );
  }

  if (!me) return null;

  const items = NAV.filter((item) => role !== null && item.roles.includes(role));

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-56 shrink-0 flex-col border-r border-hairline bg-paper md:flex">
        <Link href="/dashboard" className="border-b border-hairline px-4 py-4">
          <span className="font-serif text-[18px] font-semibold text-ink">BrandProof</span>
        </Link>
        <nav className="flex-1 space-y-0.5 overflow-y-auto p-2" aria-label="Dashboard">
          {items.map((item) => {
            const active = isActive(pathname, item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cx(
                  "flex items-center gap-2 rounded border-l-2 px-2.5 py-2 text-[13px] transition-colors",
                  active
                    ? "border-teal bg-teal-wash font-medium text-teal-dark"
                    : "border-transparent text-ink-soft hover:bg-white hover:text-ink"
                )}
                aria-current={active ? "page" : undefined}
              >
                <Icon className="h-4 w-4 shrink-0" aria-hidden />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-hairline p-3 text-[11px] text-ink-faint">
          Fictional demo data environment
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 flex items-center justify-between gap-4 border-b border-hairline bg-paper px-6 py-3">
          <div className="flex items-center gap-3">
            {me.memberships.length > 1 ? (
              <select
                value={orgId ?? undefined}
                onChange={(e) => setOrgId(Number(e.target.value))}
                className="rounded border border-hairline bg-white px-2 py-1 text-[13px] text-ink"
                aria-label="Active organisation"
              >
                {me.memberships.map((m) => (
                  <option key={m.org_id} value={m.org_id}>
                    {m.org_name}
                  </option>
                ))}
              </select>
            ) : (
              <span className="font-serif text-[15px] text-ink">
                {me.memberships[0]?.org_name ?? "Workspace"}
              </span>
            )}
            {role && <RoleTag role={role} />}
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden text-[13px] text-ink-soft sm:inline">{me.user.full_name}</span>
            <button
              onClick={() => {
                void logout().then(() => router.push("/login"));
              }}
              className="inline-flex items-center gap-1.5 rounded border border-hairline bg-white px-2.5 py-1.5 text-[12px] text-ink transition-colors hover:border-ink-faint"
            >
              <LogOut className="h-3.5 w-3.5" aria-hidden />
              Sign out
            </button>
          </div>
        </header>

        <nav className="flex gap-1 overflow-x-auto border-b border-hairline bg-paper px-4 py-2 md:hidden" aria-label="Dashboard">
          {items.map((item) => {
            const active = isActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cx(
                  "whitespace-nowrap rounded border px-2.5 py-1 text-[12px]",
                  active ? "border-teal bg-teal-wash text-teal-dark" : "border-hairline bg-white text-ink-soft"
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-8">{children}</main>
      </div>
    </div>
  );
}

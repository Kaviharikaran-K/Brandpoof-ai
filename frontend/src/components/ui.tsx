"use client";

import { useEffect } from "react";

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";

export function Button({
  variant = "secondary",
  size = "md",
  loading = false,
  disabled = false,
  className,
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: "sm" | "md";
  loading?: boolean;
}) {
  const base =
    "inline-flex items-center justify-center gap-1.5 rounded border font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60";
  const sizes = size === "sm" ? "px-2.5 py-1 text-[12px]" : "px-3.5 py-2 text-[13px]";
  const variants: Record<ButtonVariant, string> = {
    primary: "border-teal-dark bg-teal text-white hover:bg-teal-dark",
    secondary: "border-hairline bg-white text-ink hover:border-ink-faint",
    danger: "border-red-brand/40 bg-white text-red-brand hover:bg-red-wash",
    ghost: "border-transparent bg-transparent text-teal hover:underline",
  };
  return (
    <button
      className={cx(base, sizes, variants[variant], className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <span
          className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent"
          aria-hidden
        />
      )}
      {children}
    </button>
  );
}

export function Input({
  className,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cx(
        "w-full rounded border border-hairline bg-white px-2.5 py-1.5 text-[13px] text-ink placeholder:text-ink-faint",
        className
      )}
      {...props}
    />
  );
}

export function Textarea({
  className,
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cx(
        "w-full rounded border border-hairline bg-white px-2.5 py-1.5 text-[13px] text-ink placeholder:text-ink-faint",
        className
      )}
      {...props}
    />
  );
}

export function Select({
  className,
  children,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cx(
        "w-full rounded border border-hairline bg-white px-2.5 py-1.5 text-[13px] text-ink",
        className
      )}
      {...props}
    >
      {children}
    </select>
  );
}

export function Field({
  label,
  error,
  hint,
  children,
  htmlFor,
}: {
  label: string;
  error?: string | null;
  hint?: string;
  children: React.ReactNode;
  htmlFor?: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={htmlFor} className="text-[12px] font-medium text-ink-soft">
        {label}
      </label>
      {children}
      {hint && !error && <p className="text-[11px] text-ink-faint">{hint}</p>}
      {error && <p className="text-[11px] text-red-brand">{error}</p>}
    </div>
  );
}

export function Card({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={cx("rounded border border-hairline bg-white", className)}>{children}</div>
  );
}

export function StatusTag({ status }: { status: string }) {
  const styles: Record<string, string> = {
    approved: "bg-teal-wash text-teal-dark border-teal/30",
    pending: "bg-amber-wash text-amber-brand border-amber-brand/30",
    rejected: "bg-red-wash text-red-brand border-red-brand/30",
    draft: "bg-paper text-ink-soft border-hairline",
    submitted: "bg-amber-wash text-amber-brand border-amber-brand/30",
    "under analysis": "bg-amber-wash text-amber-brand border-amber-brand/30",
    "changes requested": "bg-red-wash text-red-brand border-red-brand/30",
    "clarification required": "bg-red-wash text-red-brand border-red-brand/30",
    resubmitted: "bg-teal-wash text-teal-dark border-teal/30",
  };
  return (
    <span
      className={cx(
        "inline-flex items-center rounded border px-1.5 py-0.5 text-[11px] font-medium",
        styles[status.toLowerCase()] ?? "bg-paper text-ink-soft border-hairline"
      )}
    >
      {status}
    </span>
  );
}

export function RoleTag({ role }: { role: string }) {
  return (
    <span className="inline-flex items-center rounded border border-hairline bg-paper px-1.5 py-0.5 font-mono text-[11px] text-ink-soft">
      {role}
    </span>
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3 border-b border-hairline pb-4">
      <div>
        <h1 className="font-serif text-[24px] leading-tight text-ink">{title}</h1>
        {description && <p className="mt-1 text-[13px] text-ink-soft">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Th({ children, className }: { children?: React.ReactNode; className?: string }) {
  return (
    <th
      className={cx(
        "border-b border-hairline px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wide text-ink-soft",
        className
      )}
    >
      {children}
    </th>
  );
}

export function Td({ children, className }: { children?: React.ReactNode; className?: string }) {
  return (
    <td className={cx("border-b border-hairline/70 px-3 py-2 align-top text-[13px]", className)}>
      {children}
    </td>
  );
}

export function DataTable({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cx("overflow-x-auto rounded border border-hairline bg-white", className)}>
      <table className="w-full border-collapse">{children}</table>
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx("skeleton", className)} />;
}

export function TableSkeleton({ rows = 4, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="overflow-hidden rounded border border-hairline bg-white">
      {Array.from({ length: rows }).map((_, r) => (
        <div
          key={r}
          className="flex items-center gap-4 border-b border-hairline/70 px-3 py-2.5 last:border-b-0"
        >
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className={cx("h-4", c === 0 ? "w-24" : "w-32")} />
          ))}
        </div>
      ))}
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded border border-dashed border-hairline bg-white px-6 py-10 text-center">
      {icon && <div className="mb-2 text-ink-faint">{icon}</div>}
      <p className="font-serif text-[16px] text-ink">{title}</p>
      {description && <p className="mt-1 max-w-sm text-[13px] text-ink-soft">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function Dialog({
  open,
  onClose,
  title,
  children,
  wide = false,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  wide?: boolean;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto bg-ink/30 p-6 pt-[10vh]"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={cx(
          "w-full rounded border border-hairline bg-white shadow-none",
          wide ? "max-w-2xl" : "max-w-md"
        )}
      >
        <div className="flex items-center justify-between border-b border-hairline px-4 py-3">
          <h2 className="font-serif text-[17px] text-ink">{title}</h2>
          <button
            onClick={onClose}
            className="rounded px-1.5 text-[15px] text-ink-faint hover:text-ink"
            aria-label="Close dialog"
          >
            ×
          </button>
        </div>
        <div className="px-4 py-4">{children}</div>
      </div>
    </div>
  );
}

export function ErrorNote({ children }: { children: React.ReactNode }) {
  return (
    <p className="rounded border border-red-brand/30 bg-red-wash px-3 py-2 text-[12px] text-red-brand">
      {children}
    </p>
  );
}

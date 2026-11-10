const ORG_KEY = "bp_org_id";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(message: string, status: number, detail: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export function currentOrgId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ORG_KEY);
}

export function setCurrentOrgId(orgId: number | string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ORG_KEY, String(orgId));
}

export function clearOrgId(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ORG_KEY);
}

function formatDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const loc = (item as { loc?: string[] })?.loc;
        const field = loc && loc.length > 0 ? loc[loc.length - 1] : "";
        const msg = (item as { msg?: string })?.msg ?? "";
        return field ? `${field}: ${msg}` : msg;
      })
      .join("; ");
  }
  if (detail && typeof detail === "object") {
    const inner = (detail as { detail?: unknown }).detail;
    if (inner !== undefined) return formatDetail(inner);
    return JSON.stringify(detail);
  }
  return "";
}

export async function api<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const orgId = currentOrgId();
  if (orgId && !headers.has("X-Org-Id")) headers.set("X-Org-Id", orgId);
  const hasBody = init.body !== undefined && init.body !== null;
  if (hasBody && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(path, { ...init, headers, credentials: "include" });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = (body as { detail?: unknown } | null)?.detail ?? body;
    const message = formatDetail(detail) || `Request failed (${res.status})`;
    throw new ApiError(message, res.status, detail);
  }
  if (res.status === 204) return null as T;
  return (await res.json()) as T;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

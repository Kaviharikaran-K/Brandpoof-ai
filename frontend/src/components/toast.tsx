"use client";

import { createContext, useCallback, useContext, useRef, useState } from "react";
import { AlertCircle, Check, Info } from "lucide-react";

type ToastKind = "success" | "error" | "info";

interface ToastItem {
  id: number;
  kind: ToastKind;
  title: string;
  description?: string;
}

interface ToastApi {
  push: (kind: ToastKind, title: string, description?: string) => void;
  success: (title: string, description?: string) => void;
  error: (title: string, description?: string) => void;
  info: (title: string, description?: string) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const remove = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (kind: ToastKind, title: string, description?: string) => {
      const id = nextId.current++;
      setToasts((prev) => [...prev, { id, kind, title, description }]);
      setTimeout(() => remove(id), 4200);
    },
    [remove]
  );

  const api = {
    push,
    success: (title: string, description?: string) => push("success", title, description),
    error: (title: string, description?: string) => push("error", title, description),
    info: (title: string, description?: string) => push("info", title, description),
  };

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex w-80 flex-col gap-2" role="status" aria-live="polite">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`toast-item flex items-start gap-2 rounded border border-hairline border-l-2 bg-white px-3 py-2.5 text-[13px] ${
              toast.kind === "success"
                ? "border-l-teal"
                : toast.kind === "error"
                  ? "border-l-red-brand"
                  : "border-l-ink-soft"
            }`}
          >
            <span className="mt-0.5 shrink-0">
              {toast.kind === "success" ? (
                <Check className="h-4 w-4 text-teal" aria-hidden />
              ) : toast.kind === "error" ? (
                <AlertCircle className="h-4 w-4 text-red-brand" aria-hidden />
              ) : (
                <Info className="h-4 w-4 text-ink-soft" aria-hidden />
              )}
            </span>
            <div className="min-w-0">
              <p className="font-medium text-ink">{toast.title}</p>
              {toast.description && (
                <p className="mt-0.5 text-ink-soft">{toast.description}</p>
              )}
            </div>
            <button
              onClick={() => remove(toast.id)}
              className="ml-auto shrink-0 text-ink-faint hover:text-ink"
              aria-label="Dismiss notification"
            >
              <span aria-hidden>×</span>
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside ToastProvider");
  return ctx;
}

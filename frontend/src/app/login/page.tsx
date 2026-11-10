"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button, ErrorNote, Field, Input } from "@/components/ui";
import { useToast } from "@/components/toast";
import { useAuth } from "@/lib/auth-context";

const DEMO_ACCOUNTS = [
  { role: "Admin", email: "admin@novatech.demo" },
  { role: "Creator", email: "creator@novatech.demo" },
  { role: "Reviewer", email: "reviewer@novatech.demo" },
];

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      toast.success("Signed in");
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <Link href="/" className="font-serif text-[22px] font-semibold text-ink">
            BrandProof
          </Link>
          <p className="mt-1 text-[13px] text-ink-soft">Sign in to your workspace</p>
        </div>

        <div className="rounded border border-hairline bg-white p-6">
          <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
            {error && <ErrorNote>{error}</ErrorNote>}
            <Field label="Email" htmlFor="login-email">
              <Input
                id="login-email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.example"
                required
              />
            </Field>
            <Field label="Password" htmlFor="login-password">
              <Input
                id="login-password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </Field>
            <Button type="submit" variant="primary" loading={submitting} className="w-full">
              Sign in
            </Button>
          </form>

          <p className="mt-4 border-t border-hairline pt-4 text-center text-[13px] text-ink-soft">
            No account yet?{" "}
            <Link href="/register" className="text-teal-dark hover:underline">
              Create one
            </Link>
          </p>
        </div>

        <div className="mt-4 rounded border border-hairline bg-white p-4">
          <p className="text-[12px] font-medium text-ink-soft">
            Demo accounts (fictional data · password <span className="font-mono">Demo1234!</span>)
          </p>
          <div className="mt-2 flex flex-col gap-1">
            {DEMO_ACCOUNTS.map((account) => (
              <button
                key={account.email}
                type="button"
                onClick={() => {
                  setEmail(account.email);
                  setPassword("Demo1234!");
                }}
                className="flex items-center justify-between rounded border border-hairline px-2.5 py-1.5 text-left text-[12px] text-ink transition-colors hover:border-teal hover:bg-teal-wash"
              >
                <span className="font-mono">{account.email}</span>
                <span className="text-ink-faint">{account.role}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

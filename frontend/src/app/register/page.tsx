"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button, ErrorNote, Field, Input } from "@/components/ui";
import { useToast } from "@/components/toast";
import { useAuth } from "@/lib/auth-context";

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();
  const toast = useToast();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await register(email, password, fullName);
      toast.success("Account created", "You are signed in to your new organisation.");
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
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
          <p className="mt-1 text-[13px] text-ink-soft">
            Create an account and your own organisation
          </p>
        </div>

        <div className="rounded border border-hairline bg-white p-6">
          <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
            {error && <ErrorNote>{error}</ErrorNote>}
            <Field label="Full name" htmlFor="reg-name">
              <Input
                id="reg-name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Jamie Fox"
                autoComplete="name"
                required
              />
            </Field>
            <Field label="Email" htmlFor="reg-email">
              <Input
                id="reg-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.example"
                autoComplete="email"
                required
              />
            </Field>
            <Field
              label="Password"
              htmlFor="reg-password"
              hint="At least 8 characters."
            >
              <Input
                id="reg-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="new-password"
                minLength={8}
                required
              />
            </Field>
            <Button type="submit" variant="primary" loading={submitting} className="w-full">
              Create account
            </Button>
          </form>

          <p className="mt-4 border-t border-hairline pt-4 text-center text-[13px] text-ink-soft">
            Already registered?{" "}
            <Link href="/login" className="text-teal-dark hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

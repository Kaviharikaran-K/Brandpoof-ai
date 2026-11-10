import Link from "next/link";
import { ArrowRight, BookCheck, FileSearch, ShieldCheck } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-hairline bg-paper">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <div className="flex items-baseline gap-2">
            <span className="font-serif text-[20px] font-semibold text-ink">BrandProof</span>
            <span className="hidden text-[12px] text-ink-soft sm:inline">
              Evidence-based brand governance
            </span>
          </div>
          <nav className="flex items-center gap-3">
            <Link
              href="/login"
              className="rounded border border-hairline bg-white px-3.5 py-2 text-[13px] font-medium text-ink transition-colors hover:border-ink-faint"
            >
              Sign in
            </Link>
            <Link
              href="/register"
              className="rounded border border-teal-dark bg-teal px-3.5 py-2 text-[13px] font-medium text-white transition-colors hover:bg-teal-dark"
            >
              Get started
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-6">
        <section className="border-b border-hairline py-16">
          <p className="mb-3 font-mono text-[12px] uppercase tracking-widest text-teal-dark">
            Verify · Explain · Improve · Human approval
          </p>
          <h1 className="max-w-2xl font-serif text-[40px] leading-[1.15] text-ink">
            Every claim in your copy, checked against the facts you actually approved.
          </h1>
          <p className="mt-4 max-w-xl text-[15px] leading-relaxed text-ink-soft">
            BrandProof AI is an evidence-based brand governance platform. Upload your guidelines,
            confirm each approved fact, and analyse submissions with citations back to the
            source record — people, not algorithms, make the final call.
          </p>
          <div className="mt-6 flex items-center gap-3">
            <Link
              href="/register"
              className="inline-flex items-center gap-1.5 rounded border border-teal-dark bg-teal px-4 py-2.5 text-[14px] font-medium text-white transition-colors hover:bg-teal-dark"
            >
              Create an account <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
            <Link
              href="/login"
              className="inline-flex items-center rounded border border-hairline bg-white px-4 py-2.5 text-[14px] font-medium text-ink transition-colors hover:border-ink-faint"
            >
              Sign in to the demo
            </Link>
          </div>
          <p className="mt-4 text-[12px] text-ink-faint">
            Demo accounts are pre-seeded with fictional NovaTech Solutions data.
          </p>
        </section>

        <section className="grid gap-px border-b border-hairline bg-hairline sm:grid-cols-3">
          <div className="bg-paper p-6">
            <BookCheck className="mb-3 h-5 w-5 text-teal" aria-hidden />
            <h2 className="font-serif text-[17px] text-ink">Build the evidence base</h2>
            <p className="mt-2 text-[13px] leading-relaxed text-ink-soft">
              Record approved facts, terminology rules and guidelines. Nothing is trusted until an
              admin confirms it — no silent auto-approval.
            </p>
          </div>
          <div className="bg-paper p-6">
            <FileSearch className="mb-3 h-5 w-5 text-teal" aria-hidden />
            <h2 className="font-serif text-[17px] text-ink">Analyse with citations</h2>
            <p className="mt-2 text-[13px] leading-relaxed text-ink-soft">
              Submissions are checked term by term and claim by claim. Every finding cites the fact
              ID, value, source and version it relies on.
            </p>
          </div>
          <div className="bg-paper p-6">
            <ShieldCheck className="mb-3 h-5 w-5 text-teal" aria-hidden />
            <h2 className="font-serif text-[17px] text-ink">Humans decide</h2>
            <p className="mt-2 text-[13px] leading-relaxed text-ink-soft">
              Reviewers approve, reject or request changes. Approval is never automatic, and creator
              text is never silently edited.
            </p>
          </div>
        </section>

        <section className="py-12">
          <h2 className="font-serif text-[20px] text-ink">How a submission is governed</h2>
          <ol className="mt-4 divide-y divide-hairline border-y border-hairline">
            {[
              ["Draft", "A creator writes the piece and submits it for analysis."],
              ["Analysis", "Terminology, tone, claims and evidence are checked against approved records."],
              ["Clarification", "Where evidence is missing or conflicting, a reviewer is asked — nothing is invented."],
              ["Decision", "A reviewer approves, rejects or requests changes. Every step is audited."],
            ].map(([step, text], i) => (
              <li key={step} className="flex items-baseline gap-4 py-3">
                <span className="font-mono text-[12px] text-teal-dark">{String(i + 1).padStart(2, "0")}</span>
                <span className="w-32 font-serif text-[15px] text-ink">{step}</span>
                <span className="flex-1 text-[13px] text-ink-soft">{text}</span>
              </li>
            ))}
          </ol>
        </section>
      </main>

      <footer className="border-t border-hairline bg-paper">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4 text-[12px] text-ink-faint">
          <span>BrandProof AI — fictional demo environment</span>
          <span>Verify. Explain. Improve. Human approval.</span>
        </div>
      </footer>
    </div>
  );
}

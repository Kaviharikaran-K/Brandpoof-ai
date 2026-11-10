"use client";

import { useParams } from "next/navigation";

import { SubmissionDetailView } from "@/components/submission-detail";

export default function SubmissionDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);

  if (!Number.isFinite(id)) {
    return <p className="text-[13px] text-ink-soft">Invalid submission reference.</p>;
  }

  return <SubmissionDetailView submissionId={id} />;
}

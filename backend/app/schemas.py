import datetime as dt
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

Role = Literal["admin", "creator", "reviewer"]
TermRuleType = Literal["required", "prohibited"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserOut(ORMModel):
    id: int
    email: EmailStr
    full_name: str


class MembershipOut(ORMModel):
    org_id: int
    org_name: str
    slug: str
    role: Role


class MeOut(BaseModel):
    user: UserOut
    memberships: list[MembershipOut]


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=1, max_length=160)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class OrgCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)


class OrgOut(ORMModel):
    id: int
    name: str
    slug: str
    role: Role
    created_at: dt.datetime


class MemberAddIn(BaseModel):
    email: EmailStr
    role: Role


class MemberUpdateIn(BaseModel):
    role: Role


class MemberOut(ORMModel):
    user_id: int
    email: EmailStr
    full_name: str
    role: Role
    joined_at: dt.datetime


class ProfileIn(BaseModel):
    name: str = Field(default="", max_length=160)
    product_name: str = Field(default="", max_length=160)
    tagline: str = Field(default="", max_length=240)
    tone: str = Field(default="", max_length=160)
    description: str = Field(default="", max_length=4000)


class ProfileOut(ORMModel):
    id: int
    org_id: int
    name: str
    product_name: str
    tagline: str
    tone: str
    description: str
    updated_at: dt.datetime


def _check_dates(effective: dt.date | None, expiry: dt.date | None) -> None:
    if effective is not None and expiry is not None and expiry < effective:
        raise ValueError("expiry_date cannot be before effective_date")


class FactIn(BaseModel):
    fact_id: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9][A-Za-z0-9._\-]*$")
    name: str = Field(min_length=1, max_length=160)
    approved_value: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    source_ref: str = Field(default="", max_length=300)
    version: int = Field(default=1, ge=1, le=10000)
    effective_date: dt.date | None = None
    expiry_date: dt.date | None = None

    @field_validator("fact_id")
    @classmethod
    def normalise_code(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode="after")
    def _dates(self) -> "FactIn":
        _check_dates(self.effective_date, self.expiry_date)
        return self


class FactUpdateIn(BaseModel):
    fact_id: str | None = Field(default=None, min_length=1, max_length=40, pattern=r"^[A-Za-z0-9][A-Za-z0-9._\-]*$")
    name: str | None = Field(default=None, min_length=1, max_length=160)
    approved_value: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    source_ref: str | None = Field(default=None, max_length=300)
    version: int | None = Field(default=None, ge=1, le=10000)
    effective_date: dt.date | None = None
    expiry_date: dt.date | None = None

    @model_validator(mode="after")
    def _dates(self) -> "FactUpdateIn":
        _check_dates(self.effective_date, self.expiry_date)
        return self


class FactOut(ORMModel):
    id: int
    org_id: int
    fact_id: str
    name: str
    approved_value: str
    description: str
    source_ref: str
    version: int
    effective_date: dt.date | None
    expiry_date: dt.date | None
    approval_status: str
    confirmed_at: dt.datetime | None
    created_at: dt.datetime
    updated_at: dt.datetime


class TermIn(BaseModel):
    rule_type: TermRuleType
    term: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)

    @field_validator("term")
    @classmethod
    def strip_term(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("term cannot be empty")
        return v


class TermUpdateIn(BaseModel):
    rule_type: TermRuleType | None = None
    term: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class TermOut(ORMModel):
    id: int
    org_id: int
    rule_type: str
    term: str
    description: str
    created_at: dt.datetime
    updated_at: dt.datetime


class GuidelineOut(ORMModel):
    id: int
    org_id: int
    title: str
    file_name: str
    content_type: str
    size_bytes: int
    uploaded_by_id: int | None
    created_at: dt.datetime


class SourceOut(ORMModel):
    id: int
    org_id: int
    title: str
    file_name: str
    content_type: str
    size_bytes: int
    uploaded_by_id: int | None
    created_at: dt.datetime


class AssetColourIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    colour_value: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class AssetOut(ORMModel):
    id: int
    org_id: int
    asset_type: str
    name: str
    colour_value: str | None
    file_name: str | None
    content_type: str | None
    size_bytes: int | None
    created_at: dt.datetime


class AuditOut(ORMModel):
    id: int
    action: str
    entity_type: str
    entity_id: str | None
    details: dict[str, Any]
    user_email: EmailStr | None
    created_at: dt.datetime


class Message(BaseModel):
    detail: str


class FindingOut(ORMModel):
    id: int
    finding_id: str
    category: str
    severity: str
    detected_text: str
    start_offset: int
    end_offset: int
    evidence: dict[str, Any] | None
    explanation: str
    suggested_correction: str | None
    confidence: str | None
    review_status: str
    requires_clarification: bool
    needs_human_review: bool = False


class RevisionOut(ORMModel):
    id: int
    submission_id: int
    revision_number: int
    content: str
    created_by_id: int
    created_at: dt.datetime


class AnalysisRunOut(ORMModel):
    id: int
    submission_id: int
    revision_id: int
    engine: str
    finding_count: int
    created_at: dt.datetime
    visual_report: dict[str, Any] | None = None
    findings: list[FindingOut] = []


class CommentOut(ORMModel):
    id: int
    submission_id: int
    author_email: EmailStr
    author_name: str
    body: str
    created_at: dt.datetime


class DecisionOut(ORMModel):
    id: int
    submission_id: int
    decision: str
    from_status: str
    to_status: str
    note: str
    decided_by_email: EmailStr
    decided_at: dt.datetime


class SubmissionSummaryOut(ORMModel):
    id: int
    title: str
    submission_type: str
    status: str
    created_by_id: int
    created_by_email: EmailStr | None
    current_revision_number: int | None
    revision_count: int
    latest_finding_count: int | None
    latest_clarification_count: int | None
    created_at: dt.datetime
    updated_at: dt.datetime


class SubmissionDetailOut(ORMModel):
    id: int
    org_id: int
    title: str
    submission_type: str
    status: str
    created_by_id: int
    created_by_email: EmailStr | None
    has_image: bool
    image_name: str | None
    alt_text: str | None
    created_at: dt.datetime
    updated_at: dt.datetime
    decided_at: dt.datetime | None
    revisions: list[RevisionOut]
    runs: list[AnalysisRunOut]
    comments: list[CommentOut]
    decisions: list[DecisionOut]


class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class DecisionIn(BaseModel):
    note: str = Field(default="", max_length=4000)


class StatusCount(BaseModel):
    status: str
    count: int


class CategoryCount(BaseModel):
    category: str
    count: int


class SeverityCount(BaseModel):
    severity: str
    count: int


class RepeatedIssue(BaseModel):
    category: str
    detected_text: str
    count: int


class AnalyticsTotals(BaseModel):
    submissions_total: int
    submissions_approved: int
    submissions_rejected: int
    submissions_pending: int
    submissions_draft: int
    findings_total: int
    findings_latest: int
    clarification_findings: int
    needs_human_review: int
    decided_total: int
    avg_review_hours: float | None
    avg_revision_cycles: float | None


class AnalyticsOverviewOut(BaseModel):
    totals: AnalyticsTotals
    status_counts: list[StatusCount]
    categories: list[CategoryCount]
    severities: list[SeverityCount]
    top_issues: list[RepeatedIssue]
    date_from: dt.date | None = None
    date_to: dt.date | None = None


class AnalyticsIssuesOut(BaseModel):
    categories: list[CategoryCount]
    severities: list[SeverityCount]
    repeated_terminology: list[RepeatedIssue]
    top_factual_mismatches: list[RepeatedIssue]
    top_clarification_claims: list[RepeatedIssue]
    needs_human_review: int
    date_from: dt.date | None = None
    date_to: dt.date | None = None


class TrendPoint(BaseModel):
    date: dt.date
    submissions: int
    findings: int
    decisions: int


class CategoryTrendPoint(BaseModel):
    date: dt.date
    category: str
    count: int


class AnalyticsTrendsOut(BaseModel):
    series: list[TrendPoint]
    by_category: list[CategoryTrendPoint]
    date_from: dt.date
    date_to: dt.date


class AiConsentIn(BaseModel):
    consent: bool


class AiConsentOut(BaseModel):
    consent: bool
    provider_configured: bool
    disclosure: str
    note: str
    updated_at: dt.datetime

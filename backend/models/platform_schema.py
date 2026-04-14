"""
KIRA Platform Schema Definitions

Phase 8 expands KIRA from a single assessment response into a lender-facing
platform with persistent organizations, users, kiranas, cases, alerts, and
audit events.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from models.output_schema import (
    AssessmentStatus,
    ExplanationSummary,
    PricingRecommendation,
    RepaymentCadence,
    RiskBand,
    UnderwritingDecisionPack,
    ValueRange,
)


class UserRole(str, Enum):
    """User roles supported inside a lender workspace."""

    ADMIN = "admin"
    LOAN_OFFICER = "loan_officer"


class CaseStatus(str, Enum):
    """High-level case lifecycle states for lender workflows."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    DISBURSED = "disbursed"
    MONITORING = "monitoring"
    RESTRUCTURED = "restructured"
    CLOSED = "closed"


class AlertSeverity(str, Enum):
    """Severity levels for risk or workflow alerts."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Lifecycle state for alerts."""

    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class AuditEntityType(str, Enum):
    """Entity types that can appear in the audit log."""

    ORGANIZATION = "organization"
    USER = "user"
    KIRANA = "kirana"
    CASE = "case"
    ASSESSMENT = "assessment"
    LOAN = "loan"
    ALERT = "alert"
    SYSTEM = "system"


class AuditAction(str, Enum):
    """Supported audit event actions."""

    CREATED = "created"
    UPDATED = "updated"
    STATUS_CHANGED = "status_changed"
    UNDERWRITING_OVERRIDDEN = "underwriting_overridden"
    ASSESSMENT_LINKED = "assessment_linked"
    ASSIGNED = "assigned"
    SEEDED = "seeded"
    EXPORTED = "exported"


class LenderOrg(BaseModel):
    """A lender organization or workspace."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=120)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_demo: bool = Field(default=False)


class PlatformUser(BaseModel):
    """A lender-side user with role and organization membership."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    org_id: uuid.UUID
    full_name: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., min_length=3, max_length=255)
    role: UserRole
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)


class KiranaLocation(BaseModel):
    """Normalized location fields used across kirana records and screens."""

    state: str = Field(..., min_length=1, max_length=120)
    district: str = Field(..., min_length=1, max_length=120)
    pin_code: str = Field(..., min_length=3, max_length=12)
    locality: Optional[str] = Field(default=None, max_length=200)


class KiranaProfile(BaseModel):
    """Persistent kirana borrower profile."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    org_id: uuid.UUID
    store_name: str = Field(..., min_length=1, max_length=200)
    owner_name: str = Field(..., min_length=1, max_length=200)
    owner_mobile: str = Field(..., min_length=8, max_length=20)
    location: KiranaLocation
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AssessmentSummary(BaseModel):
    """Compact assessment snapshot stored for platform workflows."""

    session_id: uuid.UUID
    assessment_id: uuid.UUID
    completed_at: datetime
    status: AssessmentStatus = Field(default=AssessmentStatus.COMPLETED)
    risk_band: Optional[RiskBand] = Field(default=None)
    risk_score: Optional[float] = Field(default=None, ge=0, le=1)
    revenue_range: Optional[ValueRange] = Field(default=None)
    loan_range: Optional[ValueRange] = Field(default=None)
    recommended_amount: Optional[float] = Field(default=None, ge=0)
    suggested_tenure_months: Optional[int] = Field(default=None, ge=6, le=60)
    estimated_emi: Optional[float] = Field(default=None, ge=0)
    emi_to_income_ratio: Optional[float] = Field(default=None, ge=0, le=1)
    repayment_cadence: Optional[RepaymentCadence] = Field(default=None)
    estimated_installment: Optional[float] = Field(default=None, ge=0)
    pricing_recommendation: Optional[PricingRecommendation] = Field(default=None)
    explanation_summary: Optional[ExplanationSummary] = Field(default=None)
    decision_pack: Optional[UnderwritingDecisionPack] = Field(default=None)
    eligible: Optional[bool] = Field(default=None)
    fraud_flagged: bool = Field(default=False)


class UnderwritingTerms(BaseModel):
    """Concrete underwriting terms used for recommendation and final approval."""

    amount: float = Field(..., ge=0)
    tenure_months: int = Field(..., ge=6, le=60)
    repayment_cadence: RepaymentCadence
    estimated_installment: float = Field(..., ge=0)
    annual_interest_rate_pct: float = Field(..., ge=0, le=60)
    processing_fee_pct: float = Field(..., ge=0, le=10)


class UnderwritingDecision(BaseModel):
    """Synthesized or persisted underwriting decision for a case."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    case_id: uuid.UUID
    org_id: uuid.UUID
    assessment_session_id: uuid.UUID
    assessment_id: uuid.UUID
    eligible: bool = Field(default=True)
    recommended_terms: Optional[UnderwritingTerms] = Field(default=None)
    final_terms: Optional[UnderwritingTerms] = Field(default=None)
    loan_range_guardrail: ValueRange = Field(...)
    pricing_recommendation: Optional[PricingRecommendation] = Field(default=None)
    policy_exception_flags: list[str] = Field(default_factory=list)
    has_override: bool = Field(default=False)
    override_reason: Optional[str] = Field(default=None, max_length=1000)
    overridden_by_user_id: Optional[uuid.UUID] = Field(default=None)
    overridden_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UnderwritingOverrideRequest(BaseModel):
    """Payload for lender-side override of recommended underwriting terms."""

    actor_user_id: uuid.UUID
    override_amount: Optional[float] = Field(default=None, ge=0)
    override_tenure_months: Optional[int] = Field(default=None, ge=6, le=60)
    override_repayment_cadence: Optional[RepaymentCadence] = Field(default=None)
    override_annual_interest_rate_pct: Optional[float] = Field(
        default=None,
        ge=0,
        le=60,
    )
    override_processing_fee_pct: Optional[float] = Field(default=None, ge=0, le=10)
    reason: str = Field(..., min_length=3, max_length=500)


class AssessmentCase(BaseModel):
    """A persistent lender-side case that can outlive a single assessment."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    org_id: uuid.UUID
    kirana_id: uuid.UUID
    created_by_user_id: uuid.UUID
    assigned_to_user_id: Optional[uuid.UUID] = Field(default=None)
    status: CaseStatus = Field(default=CaseStatus.DRAFT)
    latest_assessment_session_id: Optional[uuid.UUID] = Field(default=None)
    latest_assessment_id: Optional[uuid.UUID] = Field(default=None)
    latest_risk_band: Optional[RiskBand] = Field(default=None)
    latest_loan_range: Optional[ValueRange] = Field(default=None)
    notes: Optional[str] = Field(default=None, max_length=2000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RiskAlert(BaseModel):
    """Alert raised against a kirana or case."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    org_id: uuid.UUID
    case_id: uuid.UUID
    kirana_id: uuid.UUID
    severity: AlertSeverity
    status: AlertStatus = Field(default=AlertStatus.OPEN)
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentBundle(BaseModel):
    """Placeholder metadata for generated file bundles."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    org_id: uuid.UUID
    case_id: uuid.UUID
    documents: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LoanHistoryEntry(BaseModel):
    """Derived loan-history row for borrower detail and workspace views."""

    case_id: uuid.UUID
    status: CaseStatus
    risk_band: Optional[RiskBand] = Field(default=None)
    loan_range: Optional[ValueRange] = Field(default=None)
    updated_at: datetime
    notes: Optional[str] = Field(default=None, max_length=2000)


class StatementUploadRecord(BaseModel):
    """Placeholder record until Phase 11 statement ingestion is implemented."""

    id: str
    label: str
    status: str
    created_at: datetime
    note: str


class AuditEvent(BaseModel):
    """Immutable audit event."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    org_id: uuid.UUID
    entity_type: AuditEntityType
    entity_id: uuid.UUID
    action: AuditAction
    description: str = Field(..., min_length=1, max_length=500)
    actor_user_id: Optional[uuid.UUID] = Field(default=None)
    actor_name: Optional[str] = Field(default=None, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DashboardSummary(BaseModel):
    """Aggregated metrics for a lender workspace dashboard."""

    total_kiranas: int = Field(default=0, ge=0)
    total_cases: int = Field(default=0, ge=0)
    linked_assessments: int = Field(default=0, ge=0)
    open_alerts: int = Field(default=0, ge=0)
    flagged_assessments: int = Field(default=0, ge=0)
    cases_by_status: dict[str, int] = Field(default_factory=dict)


class CreateCaseRequest(BaseModel):
    """Request payload for creating a new lender-side case."""

    org_id: uuid.UUID
    created_by_user_id: uuid.UUID
    store_name: str = Field(..., min_length=1, max_length=200)
    owner_name: str = Field(..., min_length=1, max_length=200)
    owner_mobile: str = Field(..., min_length=8, max_length=20)
    state: str = Field(..., min_length=1, max_length=120)
    district: str = Field(..., min_length=1, max_length=120)
    pin_code: str = Field(..., min_length=3, max_length=12)
    locality: Optional[str] = Field(default=None, max_length=200)
    assigned_to_user_id: Optional[uuid.UUID] = Field(default=None)
    assessment_session_id: Optional[uuid.UUID] = Field(default=None)
    notes: Optional[str] = Field(default=None, max_length=2000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CaseStatusUpdateRequest(BaseModel):
    """Request payload for changing a case state."""

    actor_user_id: uuid.UUID
    new_status: CaseStatus
    note: Optional[str] = Field(default=None, max_length=500)


class CaseDetailResponse(BaseModel):
    """Detailed view returned for a case page."""

    case: AssessmentCase
    kirana: KiranaProfile
    latest_assessment: Optional[AssessmentSummary] = Field(default=None)
    underwriting_decision: Optional[UnderwritingDecision] = Field(default=None)
    alerts: list[RiskAlert] = Field(default_factory=list)
    audit_events: list[AuditEvent] = Field(default_factory=list)


class KiranaDetailResponse(BaseModel):
    """Detailed borrower record returned for kirana detail pages."""

    kirana: KiranaProfile
    cases: list[AssessmentCase] = Field(default_factory=list)
    assessment_history: list[AssessmentSummary] = Field(default_factory=list)
    loan_history: list[LoanHistoryEntry] = Field(default_factory=list)
    statement_uploads: list[StatementUploadRecord] = Field(default_factory=list)
    alerts: list[RiskAlert] = Field(default_factory=list)
    audit_events: list[AuditEvent] = Field(default_factory=list)


class OrgDashboardResponse(BaseModel):
    """Dashboard payload for a lender organization."""

    organization: LenderOrg
    summary: DashboardSummary
    recent_cases: list[AssessmentCase] = Field(default_factory=list)
    open_alerts: list[RiskAlert] = Field(default_factory=list)


class PlatformSnapshot(BaseModel):
    """Full demo snapshot for frontend prototyping."""

    organizations: list[LenderOrg] = Field(default_factory=list)
    users: list[PlatformUser] = Field(default_factory=list)
    kiranas: list[KiranaProfile] = Field(default_factory=list)
    cases: list[AssessmentCase] = Field(default_factory=list)
    alerts: list[RiskAlert] = Field(default_factory=list)
    audit_events: list[AuditEvent] = Field(default_factory=list)
    assessment_summaries: list[AssessmentSummary] = Field(default_factory=list)
    document_bundles: list[DocumentBundle] = Field(default_factory=list)
    underwriting_decisions: list[UnderwritingDecision] = Field(default_factory=list)

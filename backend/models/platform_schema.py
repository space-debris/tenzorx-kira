"""
KIRA Platform Schema Definitions.

This module intentionally keeps a single canonical definition for each platform
entity to avoid silent class shadowing.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

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
    ADMIN = "admin"
    LOAN_OFFICER = "loan_officer"


class CaseStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    DISBURSED = "disbursed"
    MONITORING = "monitoring"
    RESTRUCTURED = "restructured"
    CLOSED = "closed"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class AuditEntityType(str, Enum):
    ORGANIZATION = "organization"
    USER = "user"
    KIRANA = "kirana"
    CASE = "case"
    ASSESSMENT = "assessment"
    LOAN = "loan"
    ALERT = "alert"
    SYSTEM = "system"


class LoanAccountStatus(str, Enum):
    ACTIVE = "active"
    CURRENT = "current"
    OVERDUE = "overdue"
    NPA = "npa"
    RESTRUCTURED = "restructured"
    CLOSED = "closed"
    WRITTEN_OFF = "written_off"


class MonitoringRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StatementUploadStatus(str, Enum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    FAILED = "failed"


class AuditAction(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    STATUS_CHANGED = "status_changed"
    UNDERWRITING_OVERRIDDEN = "underwriting_overridden"
    ASSESSMENT_LINKED = "assessment_linked"
    ASSIGNED = "assigned"
    DECISION_RECORDED = "decision_recorded"
    SEEDED = "seeded"
    EXPORTED = "exported"
    LOAN_BOOKED = "loan_booked"
    LOAN_STATUS_CHANGED = "loan_status_changed"
    LOAN_CLOSED = "loan_closed"
    STATEMENT_UPLOADED = "statement_uploaded"
    STATEMENT_PARSED = "statement_parsed"
    MONITORING_RUN_STARTED = "monitoring_run_started"
    MONITORING_RUN_COMPLETED = "monitoring_run_completed"
    ALERT_RAISED = "alert_raised"
    RESTRUCTURING_SUGGESTED = "restructuring_suggested"


class LenderOrg(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=120)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_demo: bool = Field(default=False)


class PlatformUser(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    org_id: uuid.UUID
    full_name: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., min_length=3, max_length=255)
    role: UserRole
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)


class KiranaLocation(BaseModel):
    state: str = Field(..., min_length=1, max_length=120)
    district: str = Field(..., min_length=1, max_length=120)
    pin_code: str = Field(..., min_length=3, max_length=12)
    locality: Optional[str] = Field(default=None, max_length=200)


class KiranaProfile(BaseModel):
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
    amount: float = Field(..., ge=0)
    tenure_months: int = Field(..., ge=6, le=60)
    repayment_cadence: RepaymentCadence
    estimated_installment: float = Field(..., ge=0)
    annual_interest_rate_pct: float = Field(..., ge=0, le=60)
    processing_fee_pct: float = Field(..., ge=0, le=10)


class UnderwritingDecision(BaseModel):
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
    model_config = ConfigDict(populate_by_name=True)

    actor_user_id: uuid.UUID
    override_approved_amount: Optional[float] = Field(
        default=None,
        ge=0,
        validation_alias="override_amount",
    )
    override_tenure_months: Optional[int] = Field(default=None, ge=6, le=60)
    override_repayment_cadence: Optional[RepaymentCadence] = Field(default=None)
    override_annual_interest_rate_pct: Optional[float] = Field(default=None, ge=0, le=60)
    override_processing_fee_pct: Optional[float] = Field(default=None, ge=0, le=10)
    reason: str = Field(..., min_length=3, max_length=500)


class AssessmentCase(BaseModel):
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
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    org_id: uuid.UUID
    case_id: uuid.UUID
    documents: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    generated_by_user_id: Optional[uuid.UUID] = Field(default=None)
    export_formats: list[str] = Field(default_factory=lambda: ["json"])


class LoanDecision(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    org_id: uuid.UUID
    case_id: uuid.UUID
    assessment_session_id: Optional[uuid.UUID] = Field(default=None)
    recommended_amount: float = Field(..., ge=0)
    approved_amount: float = Field(..., ge=0)
    recommended_tenure_months: int = Field(..., ge=3, le=60)
    approved_tenure_months: int = Field(..., ge=3, le=60)
    pricing_rate_annual: float = Field(..., ge=0)
    processing_fee_rate: float = Field(..., ge=0)
    repayment_cadence: str = Field(default="monthly", min_length=3, max_length=20)
    decision_reason: str = Field(..., min_length=1, max_length=1000)
    override_reason: Optional[str] = Field(default=None, max_length=1000)
    created_by_user_id: uuid.UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TransactionSummary(BaseModel):
    total_credits: float = Field(default=0.0, ge=0)
    total_debits: float = Field(default=0.0, ge=0)
    credit_count: int = Field(default=0, ge=0)
    debit_count: int = Field(default=0, ge=0)
    avg_daily_balance: float = Field(default=0.0, ge=0)
    period_days: int = Field(default=0, ge=0)
    start_date: Optional[datetime] = Field(default=None)
    end_date: Optional[datetime] = Field(default=None)


class UtilizationBreakdown(BaseModel):
    supplier_inventory_pct: float = Field(default=0.0, ge=0, le=100)
    transfer_wallet_pct: float = Field(default=0.0, ge=0, le=100)
    personal_cash_pct: float = Field(default=0.0, ge=0, le=100)
    unknown_pct: float = Field(default=0.0, ge=0, le=100)
    flags: list[str] = Field(default_factory=list)
    diversion_risk: str = Field(default="low")


class RestructuringSuggestion(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    loan_id: uuid.UUID
    case_id: uuid.UUID
    org_id: uuid.UUID
    trigger: str = Field(..., min_length=1, max_length=300)
    suggestion_type: str = Field(default="tenure_extension")
    suggested_tenure_extension_months: Optional[int] = Field(default=None, ge=1, le=24)
    suggested_emi_reduction_pct: Optional[float] = Field(default=None, ge=0, le=50)
    suggested_moratorium_months: Optional[int] = Field(default=None, ge=1, le=6)
    rationale: str = Field(..., min_length=1, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LoanAccount(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    org_id: uuid.UUID
    case_id: uuid.UUID
    kirana_id: uuid.UUID
    assessment_session_id: uuid.UUID
    status: LoanAccountStatus = Field(default=LoanAccountStatus.ACTIVE)
    principal_amount: float = Field(..., ge=0)
    tenure_months: int = Field(..., ge=6, le=60)
    repayment_cadence: RepaymentCadence
    annual_interest_rate_pct: float = Field(..., ge=0, le=60)
    processing_fee_pct: float = Field(..., ge=0, le=10)
    estimated_installment: float = Field(default=0.0, ge=0)
    disbursed_at: Optional[datetime] = Field(default=None)
    maturity_date: Optional[datetime] = Field(default=None)
    outstanding_principal: Optional[float] = Field(default=None, ge=0)
    total_collected: float = Field(default=0.0, ge=0)
    last_collection_date: Optional[datetime] = Field(default=None)
    days_past_due: int = Field(default=0, ge=0)
    utilization: Optional[UtilizationBreakdown] = Field(default=None)
    original_risk_band: Optional[RiskBand] = Field(default=None)
    original_revenue_range: Optional[ValueRange] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StatementUpload(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    org_id: uuid.UUID
    case_id: uuid.UUID
    loan_id: uuid.UUID
    kirana_id: uuid.UUID
    status: StatementUploadStatus = Field(default=StatementUploadStatus.UPLOADED)
    file_name: str = Field(..., min_length=1, max_length=255)
    file_type: str = Field(default="pdf")
    file_size_bytes: int = Field(default=0, ge=0)
    transaction_summary: Optional[TransactionSummary] = Field(default=None)
    parse_error: Optional[str] = Field(default=None, max_length=500)
    uploaded_by_user_id: Optional[uuid.UUID] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MonitoringRun(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    org_id: uuid.UUID
    case_id: uuid.UUID
    loan_id: uuid.UUID
    kirana_id: uuid.UUID
    status: MonitoringRunStatus = Field(default=MonitoringRunStatus.PENDING)
    statement_upload_id: Optional[uuid.UUID] = Field(default=None)
    previous_risk_band: Optional[RiskBand] = Field(default=None)
    new_risk_band: Optional[RiskBand] = Field(default=None)
    new_risk_score: Optional[float] = Field(default=None, ge=0, le=1)
    inflow_velocity_change_pct: Optional[float] = Field(default=None)
    utilization: Optional[UtilizationBreakdown] = Field(default=None)
    alerts_raised: list[str] = Field(default_factory=list)
    restructuring_suggestion: Optional[RestructuringSuggestion] = Field(default=None)
    run_notes: Optional[str] = Field(default=None, max_length=1000)
    completed_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AuditEvent(BaseModel):
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


class LoanHistoryEntry(BaseModel):
    case_id: uuid.UUID
    status: CaseStatus
    risk_band: Optional[RiskBand] = Field(default=None)
    loan_range: Optional[ValueRange] = Field(default=None)
    updated_at: datetime
    notes: Optional[str] = Field(default=None, max_length=2000)


class StatementUploadRecord(BaseModel):
    id: str
    label: str
    status: str
    created_at: datetime
    note: str
    transaction_count: int = Field(default=0, ge=0)
    inflow_total: float = Field(default=0, ge=0)
    outflow_total: float = Field(default=0, ge=0)


class MonitoringRunRecord(BaseModel):
    id: str
    created_at: datetime
    current_risk_band: Optional[RiskBand] = Field(default=None)
    inflow_change_ratio: float = Field(default=0.0)
    stress_score: float = Field(default=0.0, ge=0, le=1)
    restructuring_recommendation: Optional[str] = Field(default=None)
    utilization_breakdown: dict[str, float] = Field(default_factory=dict)


class DashboardSummary(BaseModel):
    total_kiranas: int = Field(default=0, ge=0)
    total_cases: int = Field(default=0, ge=0)
    linked_assessments: int = Field(default=0, ge=0)
    open_alerts: int = Field(default=0, ge=0)
    flagged_assessments: int = Field(default=0, ge=0)
    cases_by_status: dict[str, int] = Field(default_factory=dict)


class CreateCaseRequest(BaseModel):
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
    actor_user_id: uuid.UUID
    new_status: CaseStatus
    note: Optional[str] = Field(default=None, max_length=500)


class CaseDetailResponse(BaseModel):
    case: AssessmentCase
    kirana: KiranaProfile
    latest_assessment: Optional[AssessmentSummary] = Field(default=None)
    underwriting_decision: Optional[UnderwritingDecision] = Field(default=None)
    alerts: list[RiskAlert] = Field(default_factory=list)
    audit_events: list[AuditEvent] = Field(default_factory=list)


class KiranaDetailResponse(BaseModel):
    kirana: KiranaProfile
    cases: list[AssessmentCase] = Field(default_factory=list)
    assessment_history: list[AssessmentSummary] = Field(default_factory=list)
    loan_history: list[LoanHistoryEntry] = Field(default_factory=list)
    statement_uploads: list[StatementUploadRecord] = Field(default_factory=list)
    monitoring_runs: list[MonitoringRunRecord] = Field(default_factory=list)
    alerts: list[RiskAlert] = Field(default_factory=list)
    audit_events: list[AuditEvent] = Field(default_factory=list)


class LoanAccountDetailResponse(BaseModel):
    loan_account: LoanAccount
    case: AssessmentCase
    kirana: KiranaProfile
    loan_decision: Optional[LoanDecision] = Field(default=None)
    statement_uploads: list[StatementUploadRecord] = Field(default_factory=list)
    monitoring_runs: list[MonitoringRunRecord] = Field(default_factory=list)
    alerts: list[RiskAlert] = Field(default_factory=list)
    audit_events: list[AuditEvent] = Field(default_factory=list)


class StatementUploadCreateRequest(BaseModel):
    actor_user_id: uuid.UUID
    file_name: str = Field(..., min_length=1, max_length=255)
    file_type: str = Field(..., min_length=1, max_length=128)
    source_kind: str = Field(default="bank", min_length=3, max_length=30)
    content: str = Field(..., min_length=1)


class StatementUploadResponse(BaseModel):
    statement_upload: StatementUploadRecord
    monitoring_run: MonitoringRunRecord
    alerts: list[RiskAlert] = Field(default_factory=list)


class PortfolioMetricCard(BaseModel):
    label: str
    value: float | int
    trend_label: Optional[str] = Field(default=None)


class PortfolioAnalyticsResponse(BaseModel):
    metrics: list[PortfolioMetricCard] = Field(default_factory=list)
    risk_distribution: dict[str, int] = Field(default_factory=dict)
    geography_distribution: dict[str, int] = Field(default_factory=dict)
    status_distribution: dict[str, int] = Field(default_factory=dict)
    cohorts: list[dict[str, Any]] = Field(default_factory=list)
    loans: list[dict[str, Any]] = Field(default_factory=list)


class DocumentBundleResponse(BaseModel):
    bundle: DocumentBundle
    payload: dict[str, Any] = Field(default_factory=dict)


class OrgDashboardResponse(BaseModel):
    organization: LenderOrg
    summary: DashboardSummary
    recent_cases: list[AssessmentCase] = Field(default_factory=list)
    open_alerts: list[RiskAlert] = Field(default_factory=list)


class PlatformSnapshot(BaseModel):
    organizations: list[LenderOrg] = Field(default_factory=list)
    users: list[PlatformUser] = Field(default_factory=list)
    kiranas: list[KiranaProfile] = Field(default_factory=list)
    cases: list[AssessmentCase] = Field(default_factory=list)
    alerts: list[RiskAlert] = Field(default_factory=list)
    audit_events: list[AuditEvent] = Field(default_factory=list)
    assessment_summaries: list[AssessmentSummary] = Field(default_factory=list)
    loan_decisions: list[LoanDecision] = Field(default_factory=list)
    loan_accounts: list[LoanAccount] = Field(default_factory=list)
    statement_uploads: list[StatementUpload] = Field(default_factory=list)
    monitoring_runs: list[MonitoringRun] = Field(default_factory=list)
    document_bundles: list[DocumentBundle] = Field(default_factory=list)
    underwriting_decisions: list[UnderwritingDecision] = Field(default_factory=list)


class BookLoanRequest(BaseModel):
    actor_user_id: uuid.UUID
    case_id: uuid.UUID
    disbursement_date: Optional[datetime] = Field(default=None)
    note: Optional[str] = Field(default=None, max_length=500)


class LoanStatusUpdateRequest(BaseModel):
    actor_user_id: uuid.UUID
    new_status: LoanAccountStatus
    days_past_due: Optional[int] = Field(default=None, ge=0)
    note: Optional[str] = Field(default=None, max_length=500)

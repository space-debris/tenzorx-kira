"""
Case service for Phase 8 lender-platform workflows.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from models.output_schema import RepaymentCadence, ValueRange
from models.platform_schema import (
    AlertStatus,
    AssessmentCase,
    AssessmentSummary,
    AuditAction,
    AuditEntityType,
    CaseDetailResponse,
    CaseStatus,
    CaseStatusUpdateRequest,
    CreateCaseRequest,
    KiranaLocation,
    KiranaDetailResponse,
    KiranaProfile,
    LoanHistoryEntry,
    MonitoringRunRecord,
    OrgDashboardResponse,
    StatementUploadRecord,
    UnderwritingDecision,
    UnderwritingOverrideRequest,
    UnderwritingTerms,
)
from services.audit_service import AuditService
from services.loan_service import LoanService
from storage.repository import PlatformRepository

ALLOWED_STATUS_TRANSITIONS: dict[CaseStatus, set[CaseStatus]] = {
    CaseStatus.DRAFT: {CaseStatus.SUBMITTED},
    CaseStatus.SUBMITTED: {CaseStatus.UNDER_REVIEW, CaseStatus.CLOSED},
    CaseStatus.UNDER_REVIEW: {CaseStatus.APPROVED, CaseStatus.CLOSED},
    CaseStatus.APPROVED: {CaseStatus.DISBURSED, CaseStatus.CLOSED},
    CaseStatus.DISBURSED: {CaseStatus.MONITORING, CaseStatus.CLOSED},
    CaseStatus.MONITORING: {CaseStatus.RESTRUCTURED, CaseStatus.CLOSED},
    CaseStatus.RESTRUCTURED: {CaseStatus.MONITORING, CaseStatus.CLOSED},
    CaseStatus.CLOSED: set(),
}


class CaseService:
    """Coordinates persistent case and kirana operations for lenders."""

    def __init__(
        self,
        repository: PlatformRepository,
        audit_service: AuditService,
        loan_service: LoanService | None = None,
    ) -> None:
        self.repository = repository
        self.audit_service = audit_service
        self.loan_service = loan_service

    def create_case(self, payload: CreateCaseRequest) -> CaseDetailResponse:
        org = self.repository.get_organization(payload.org_id)
        if org is None:
            raise ValueError("Organization not found")

        created_by = self.repository.get_user(payload.created_by_user_id)
        if created_by is None or created_by.org_id != payload.org_id:
            raise ValueError("Creating user is invalid for this organization")

        if payload.assigned_to_user_id is not None:
            assigned_to = self.repository.get_user(payload.assigned_to_user_id)
            if assigned_to is None or assigned_to.org_id != payload.org_id:
                raise ValueError("Assigned user is invalid for this organization")

        latest_summary = None
        initial_status = CaseStatus.DRAFT
        if payload.assessment_session_id is not None:
            latest_summary = self.repository.get_assessment_summary(payload.assessment_session_id)
            if latest_summary is None:
                raise ValueError("Assessment session could not be found")
            initial_status = CaseStatus.UNDER_REVIEW

        now = datetime.utcnow()
        kirana = KiranaProfile(
            org_id=payload.org_id,
            store_name=payload.store_name,
            owner_name=payload.owner_name,
            owner_mobile=payload.owner_mobile,
            location=KiranaLocation(
                state=payload.state,
                district=payload.district,
                pin_code=payload.pin_code,
                locality=payload.locality,
            ),
            metadata=payload.metadata,
            created_at=now,
            updated_at=now,
        )
        self.repository.create_kirana(kirana)

        case = AssessmentCase(
            org_id=payload.org_id,
            kirana_id=kirana.id,
            created_by_user_id=payload.created_by_user_id,
            assigned_to_user_id=payload.assigned_to_user_id,
            status=initial_status,
            latest_assessment_session_id=(
                latest_summary.session_id if latest_summary is not None else None
            ),
            latest_assessment_id=(
                latest_summary.assessment_id if latest_summary is not None else None
            ),
            latest_risk_band=latest_summary.risk_band if latest_summary is not None else None,
            latest_loan_range=latest_summary.loan_range if latest_summary is not None else None,
            notes=payload.notes,
            created_at=now,
            updated_at=now,
        )
        self.repository.create_case(case)

        self.audit_service.record_event(
            org_id=payload.org_id,
            entity_type=AuditEntityType.KIRANA,
            entity_id=kirana.id,
            action=AuditAction.CREATED,
            description=f"Created kirana profile for {kirana.store_name}",
            actor_user_id=payload.created_by_user_id,
            metadata={"pin_code": kirana.location.pin_code},
        )
        self.audit_service.record_event(
            org_id=payload.org_id,
            entity_type=AuditEntityType.CASE,
            entity_id=case.id,
            action=AuditAction.CREATED,
            description=f"Created case for {kirana.store_name}",
            actor_user_id=payload.created_by_user_id,
            metadata={"status": case.status.value},
        )

        if latest_summary is not None:
            self.audit_service.record_event(
                org_id=payload.org_id,
                entity_type=AuditEntityType.ASSESSMENT,
                entity_id=latest_summary.assessment_id,
                action=AuditAction.ASSESSMENT_LINKED,
                description=f"Linked assessment {latest_summary.session_id} to case {case.id}",
                actor_user_id=payload.created_by_user_id,
                metadata={
                    "case_id": str(case.id),
                    "session_id": str(latest_summary.session_id),
                },
            )

        return self.get_case_detail(case.id)

    def link_assessment_to_case(
        self,
        case_id: uuid.UUID,
        session_id: uuid.UUID,
        actor_user_id: uuid.UUID | None = None,
    ) -> CaseDetailResponse:
        case = self.repository.get_case(case_id)
        if case is None:
            raise ValueError("Case not found")

        summary = self.repository.get_assessment_summary(session_id)
        if summary is None:
            raise ValueError("Assessment session could not be found")

        updated_case = case.model_copy(
            update={
                "latest_assessment_session_id": summary.session_id,
                "latest_assessment_id": summary.assessment_id,
                "latest_risk_band": summary.risk_band,
                "latest_loan_range": summary.loan_range,
                "status": (
                    CaseStatus.UNDER_REVIEW
                    if case.status == CaseStatus.DRAFT
                    else case.status
                ),
                "updated_at": datetime.utcnow(),
            }
        )
        self.repository.update_case(updated_case)

        self.audit_service.record_event(
            org_id=updated_case.org_id,
            entity_type=AuditEntityType.CASE,
            entity_id=updated_case.id,
            action=AuditAction.ASSESSMENT_LINKED,
            description=f"Linked assessment {summary.session_id} to case",
            actor_user_id=actor_user_id,
            metadata={"assessment_id": str(summary.assessment_id)},
        )
        return self.get_case_detail(case_id)

    def update_case_status(
        self,
        case_id: uuid.UUID,
        payload: CaseStatusUpdateRequest,
    ) -> CaseDetailResponse:
        case = self.repository.get_case(case_id)
        if case is None:
            raise ValueError("Case not found")

        actor = self.repository.get_user(payload.actor_user_id)
        if actor is None or actor.org_id != case.org_id:
            raise ValueError("Actor is invalid for this organization")
        if payload.new_status == case.status:
            raise ValueError("Case is already in the requested status")
        allowed = ALLOWED_STATUS_TRANSITIONS.get(case.status, set())
        if payload.new_status not in allowed:
            raise ValueError(
                f"Invalid status transition from {case.status.value} to {payload.new_status.value}"
            )
        if payload.new_status == CaseStatus.APPROVED and case.latest_loan_range is None:
            raise ValueError("Cannot approve a case before an assessment is linked")

        updated_case = case.model_copy(
            update={
                "status": payload.new_status,
                "notes": payload.note or case.notes,
                "updated_at": datetime.utcnow(),
            }
        )
        self.repository.update_case(updated_case)

        if self.loan_service is not None:
            if payload.new_status == CaseStatus.APPROVED:
                self.loan_service.ensure_decision_for_case(updated_case, payload.actor_user_id, payload.note)
            elif payload.new_status == CaseStatus.DISBURSED:
                self.loan_service.ensure_loan_account_for_case(updated_case, payload.actor_user_id)
            self.loan_service.sync_loan_status(updated_case)

        self.audit_service.record_event(
            org_id=case.org_id,
            entity_type=AuditEntityType.CASE,
            entity_id=case.id,
            action=AuditAction.STATUS_CHANGED,
            description=f"Changed case status from {case.status.value} to {payload.new_status.value}",
            actor_user_id=payload.actor_user_id,
            metadata={
                "previous_status": case.status.value,
                "new_status": payload.new_status.value,
                "note": payload.note,
            },
        )
        return self.get_case_detail(case_id)

    def list_cases_for_org(self, org_id: uuid.UUID) -> list[AssessmentCase]:
        org = self.repository.get_organization(org_id)
        if org is None:
            raise ValueError("Organization not found")
        return self.repository.list_cases(org_id)

    def list_kiranas_for_org(self, org_id: uuid.UUID) -> list[KiranaProfile]:
        org = self.repository.get_organization(org_id)
        if org is None:
            raise ValueError("Organization not found")
        return self.repository.list_kiranas(org_id)

    def get_case_detail(self, case_id: uuid.UUID) -> CaseDetailResponse:
        case = self.repository.get_case(case_id)
        if case is None:
            raise ValueError("Case not found")

        kirana = self.repository.get_kirana(case.kirana_id)
        if kirana is None:
            raise ValueError("Kirana not found for case")

        latest_assessment = None
        if case.latest_assessment_session_id is not None:
            latest_assessment = self.repository.get_assessment_summary(
                case.latest_assessment_session_id
            )

        alerts = self.repository.list_alerts(case_id=case.id)
        audit_events = self.repository.list_audit_events(entity_id=case.id)
        audit_events.extend(self.repository.list_audit_events(entity_id=kirana.id))
        audit_events = sorted(
            {str(event.id): event for event in audit_events}.values(),
            key=lambda item: item.created_at,
            reverse=True,
        )

        return CaseDetailResponse(
            case=case,
            kirana=kirana,
            latest_assessment=latest_assessment,
            underwriting_decision=self._resolve_underwriting_decision(case, latest_assessment),
            alerts=alerts,
            audit_events=audit_events,
        )

    def get_kirana_detail(
        self,
        org_id: uuid.UUID,
        kirana_id: uuid.UUID,
    ) -> KiranaDetailResponse:
        org = self.repository.get_organization(org_id)
        if org is None:
            raise ValueError("Organization not found")

        kirana = self.repository.get_kirana(kirana_id)
        if kirana is None or kirana.org_id != org_id:
            raise ValueError("Kirana not found")

        cases = [
            case for case in self.repository.list_cases(org_id)
            if case.kirana_id == kirana_id
        ]

        assessment_history: list[AssessmentSummary] = []
        for case in cases:
            if case.latest_assessment_session_id is None:
                continue
            summary = self.repository.get_assessment_summary(case.latest_assessment_session_id)
            if summary is not None:
                assessment_history.append(summary)
        assessment_history.sort(key=lambda item: item.completed_at, reverse=True)

        alerts = self.repository.list_alerts(org_id=org_id, kirana_id=kirana_id)

        loan_statuses = {
            CaseStatus.APPROVED,
            CaseStatus.DISBURSED,
            CaseStatus.MONITORING,
            CaseStatus.RESTRUCTURED,
            CaseStatus.CLOSED,
        }
        loan_history = [
            LoanHistoryEntry(
                case_id=case.id,
                status=case.status,
                risk_band=case.latest_risk_band,
                loan_range=case.latest_loan_range,
                updated_at=case.updated_at,
                notes=case.notes,
            )
            for case in cases
            if case.status in loan_statuses or case.latest_loan_range is not None
        ]
        loan_history.sort(key=lambda item: item.updated_at, reverse=True)

        statement_uploads: list[StatementUploadRecord] = []
        for upload in self.repository.list_statement_uploads(org_id=org_id):
            if upload.case_id not in {case.id for case in cases}:
                continue
            statement_uploads.append(
                StatementUploadRecord(
                    id=str(upload.id),
                    label=upload.file_name,
                    status=upload.status.value if hasattr(upload.status, "value") else str(upload.status),
                    created_at=upload.created_at,
                    note=f"Uploaded {upload.file_name}",
                    transaction_count=(upload.transaction_summary.credit_count + upload.transaction_summary.debit_count) if upload.transaction_summary else 0,
                    inflow_total=upload.transaction_summary.total_credits if upload.transaction_summary else 0.0,
                    outflow_total=upload.transaction_summary.total_debits if upload.transaction_summary else 0.0,
                )
            )

        monitoring_runs: list[MonitoringRunRecord] = []
        for run in self.repository.list_monitoring_runs(org_id=org_id):
            if run.case_id not in {case.id for case in cases}:
                continue
            monitoring_runs.append(
                MonitoringRunRecord(
                    id=str(run.id),
                    created_at=run.created_at,
                    current_risk_band=run.current_risk_band,
                    inflow_change_ratio=run.inflow_change_ratio,
                    stress_score=run.stress_score,
                    restructuring_recommendation=run.restructuring_recommendation,
                    utilization_breakdown=run.utilization_breakdown,
                )
            )

        audit_events = self.repository.list_audit_events(entity_id=kirana.id)
        for case in cases:
            audit_events.extend(self.repository.list_audit_events(entity_id=case.id))
        audit_events = sorted(
            {str(event.id): event for event in audit_events}.values(),
            key=lambda item: item.created_at,
            reverse=True,
        )

        return KiranaDetailResponse(
            kirana=kirana,
            cases=cases,
            assessment_history=assessment_history,
            loan_history=loan_history,
            statement_uploads=statement_uploads,
            monitoring_runs=monitoring_runs,
            alerts=alerts,
            audit_events=audit_events,
        )

    def upsert_kirana_from_assessment(
        self,
        org_id: uuid.UUID,
        store_name: str,
        owner_name: str | None = None,
        owner_mobile: str | None = None,
        state: str | None = None,
        district: str | None = None,
        pin_code: str | None = None,
        locality: str | None = None,
        shop_size: str | None = None,
        rent: float | None = None,
        years_in_operation: float | None = None,
    ) -> KiranaProfile:
        """Find existing kirana by name+pin or create a new one. Update metadata either way."""
        now = datetime.utcnow()
        safe_pin = pin_code or "000000"
        safe_state = state or "Unknown"
        safe_district = district or "Unknown"

        existing = self.repository.find_kirana(org_id, store_name, safe_pin)

        metadata: dict = {}
        if shop_size:
            metadata["shop_size"] = shop_size
        if rent is not None:
            metadata["rent"] = rent
        if years_in_operation is not None:
            metadata["years_in_operation"] = years_in_operation

        if existing is not None:
            updated = existing.model_copy(
                update={
                    "metadata": {**existing.metadata, **metadata},
                    "updated_at": now,
                    **({"owner_name": owner_name} if owner_name else {}),
                    **({"owner_mobile": owner_mobile} if owner_mobile else {}),
                }
            )
            self.repository.update_kirana(updated)
            return updated

        kirana = KiranaProfile(
            org_id=org_id,
            store_name=store_name,
            owner_name=owner_name or "Unknown",
            owner_mobile=owner_mobile or "N/A",
            location=KiranaLocation(
                state=safe_state,
                district=safe_district,
                pin_code=safe_pin,
                locality=locality,
            ),
            metadata=metadata,
            created_at=now,
            updated_at=now,
        )
        self.repository.create_kirana(kirana)
        return kirana

    def create_case_from_assessment(
        self,
        org_id: uuid.UUID,
        created_by_user_id: uuid.UUID,
        kirana_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> AssessmentCase:
        """Auto-create a case linked to a kirana and assessment (standalone assessment flow)."""
        org = self.repository.get_organization(org_id)
        if org is None:
            raise ValueError("Organization not found")

        summary = self.repository.get_assessment_summary(session_id)

        now = datetime.utcnow()
        case = AssessmentCase(
            org_id=org_id,
            kirana_id=kirana_id,
            created_by_user_id=created_by_user_id,
            assigned_to_user_id=created_by_user_id,
            status=CaseStatus.UNDER_REVIEW if summary else CaseStatus.DRAFT,
            latest_assessment_session_id=summary.session_id if summary else None,
            latest_assessment_id=summary.assessment_id if summary else None,
            latest_risk_band=summary.risk_band if summary else None,
            latest_loan_range=summary.loan_range if summary else None,
            notes="Auto-created from standalone assessment.",
            created_at=now,
            updated_at=now,
        )
        self.repository.create_case(case)

        kirana = self.repository.get_kirana(kirana_id)
        kirana_name = kirana.store_name if kirana else "Unknown"

        self.audit_service.record_event(
            org_id=org_id,
            entity_type=AuditEntityType.CASE,
            entity_id=case.id,
            action=AuditAction.CREATED,
            description=f"Auto-created case for {kirana_name} from assessment",
            actor_user_id=created_by_user_id,
            metadata={"source": "standalone_assessment", "session_id": str(session_id)},
        )

        if summary:
            self.audit_service.record_event(
                org_id=org_id,
                entity_type=AuditEntityType.ASSESSMENT,
                entity_id=summary.assessment_id,
                action=AuditAction.ASSESSMENT_LINKED,
                description=f"Linked assessment {session_id} to auto-created case {case.id}",
                actor_user_id=created_by_user_id,
                metadata={"case_id": str(case.id), "session_id": str(session_id)},
            )

        return case

    def get_org_dashboard(self, org_id: uuid.UUID) -> OrgDashboardResponse:
        org = self.repository.get_organization(org_id)
        if org is None:
            raise ValueError("Organization not found")

        summary = self.repository.build_dashboard_summary(org_id)
        recent_cases = self.repository.list_cases(org_id)[:5]
        open_alerts = self.repository.list_alerts(
            org_id=org_id,
            status=AlertStatus.OPEN,
        )[:5]

        return OrgDashboardResponse(
            organization=org,
            summary=summary,
            recent_cases=recent_cases,
            open_alerts=open_alerts,
        )

    def override_underwriting_decision(
        self,
        case_id: uuid.UUID,
        payload: UnderwritingOverrideRequest,
    ) -> CaseDetailResponse:
        case = self.repository.get_case(case_id)
        if case is None:
            raise ValueError("Case not found")

        actor = self.repository.get_user(payload.actor_user_id)
        if actor is None or actor.org_id != case.org_id:
            raise ValueError("Actor is invalid for this organization")

        if case.latest_assessment_session_id is None:
            raise ValueError("Case has no assessment to override")

        latest_summary = self.repository.get_assessment_summary(case.latest_assessment_session_id)
        if latest_summary is None:
            raise ValueError("Latest assessment summary could not be found")

        recommended_terms = self._build_underwriting_terms(latest_summary)
        if recommended_terms is None:
            raise ValueError("Latest assessment does not include an eligible underwriting recommendation")

        final_terms = UnderwritingTerms(
            amount=payload.override_amount if payload.override_amount is not None else recommended_terms.amount,
            tenure_months=(
                payload.override_tenure_months
                if payload.override_tenure_months is not None
                else recommended_terms.tenure_months
            ),
            repayment_cadence=(
                payload.override_repayment_cadence
                if payload.override_repayment_cadence is not None
                else recommended_terms.repayment_cadence
            ),
            estimated_installment=self._estimate_override_installment(
                latest_summary=latest_summary,
                recommended_terms=recommended_terms,
                amount=payload.override_amount if payload.override_amount is not None else recommended_terms.amount,
                tenure_months=(
                    payload.override_tenure_months
                    if payload.override_tenure_months is not None
                    else recommended_terms.tenure_months
                ),
                cadence=(
                    payload.override_repayment_cadence
                    if payload.override_repayment_cadence is not None
                    else recommended_terms.repayment_cadence
                ),
            ),
            annual_interest_rate_pct=(
                payload.override_annual_interest_rate_pct
                if payload.override_annual_interest_rate_pct is not None
                else recommended_terms.annual_interest_rate_pct
            ),
            processing_fee_pct=(
                payload.override_processing_fee_pct
                if payload.override_processing_fee_pct is not None
                else recommended_terms.processing_fee_pct
            ),
        )

        if final_terms == recommended_terms:
            raise ValueError("Override must change at least one underwriting input")

        policy_flags = self._derive_policy_exception_flags(
            latest_summary=latest_summary,
            recommended_terms=recommended_terms,
            final_terms=final_terms,
        )
        now = datetime.utcnow()
        decision = UnderwritingDecision(
            case_id=case.id,
            org_id=case.org_id,
            assessment_session_id=latest_summary.session_id,
            assessment_id=latest_summary.assessment_id,
            eligible=bool(latest_summary.eligible),
            recommended_terms=recommended_terms,
            final_terms=final_terms,
            loan_range_guardrail=latest_summary.loan_range or ValueRange(low=0, high=0),
            pricing_recommendation=latest_summary.pricing_recommendation,
            policy_exception_flags=policy_flags,
            has_override=True,
            override_reason=payload.reason,
            overridden_by_user_id=payload.actor_user_id,
            overridden_at=now,
            created_at=now,
            updated_at=now,
        )
        self.repository.save_underwriting_decision(decision)

        self.audit_service.record_event(
            org_id=case.org_id,
            entity_type=AuditEntityType.CASE,
            entity_id=case.id,
            action=AuditAction.UNDERWRITING_OVERRIDDEN,
            description="Captured underwriting override for latest assessment",
            actor_user_id=payload.actor_user_id,
            metadata={
                "assessment_session_id": str(latest_summary.session_id),
                "reason": payload.reason,
                "policy_exception_flags": policy_flags,
                "recommended_terms": recommended_terms.model_dump(mode="json"),
                "final_terms": final_terms.model_dump(mode="json"),
            },
        )

        return self.get_case_detail(case_id)

    def _resolve_underwriting_decision(
        self,
        case: AssessmentCase,
        latest_summary: AssessmentSummary | None,
    ) -> UnderwritingDecision | None:
        if latest_summary is None:
            return None

        persisted = self.repository.get_latest_underwriting_decision(
            case.id,
            latest_summary.session_id,
        )
        if persisted is not None:
            return persisted

        recommended_terms = self._build_underwriting_terms(latest_summary)

        return UnderwritingDecision(
            case_id=case.id,
            org_id=case.org_id,
            assessment_session_id=latest_summary.session_id,
            assessment_id=latest_summary.assessment_id,
            eligible=bool(latest_summary.eligible),
            recommended_terms=recommended_terms,
            final_terms=recommended_terms,
            loan_range_guardrail=latest_summary.loan_range or ValueRange(low=0, high=0),
            pricing_recommendation=latest_summary.pricing_recommendation,
            policy_exception_flags=[],
            has_override=False,
            created_at=latest_summary.completed_at,
            updated_at=latest_summary.completed_at,
        )

    def _build_underwriting_terms(
        self,
        summary: AssessmentSummary,
    ) -> UnderwritingTerms | None:
        if not summary.eligible or summary.loan_range is None:
            return None

        pricing = summary.pricing_recommendation
        amount = summary.recommended_amount
        if amount is None:
            amount = (summary.loan_range.low + summary.loan_range.high) / 2.0

        cadence = summary.repayment_cadence or RepaymentCadence.WEEKLY
        installment = summary.estimated_installment
        if installment is None:
            installment = summary.estimated_emi or 0.0

        return UnderwritingTerms(
            amount=round(amount, 2),
            tenure_months=summary.suggested_tenure_months or 18,
            repayment_cadence=cadence,
            estimated_installment=round(installment, 2),
            annual_interest_rate_pct=(
                pricing.annual_interest_rate_pct if pricing is not None else 18.0
            ),
            processing_fee_pct=(
                pricing.processing_fee_pct if pricing is not None else 1.5
            ),
        )

    def _estimate_override_installment(
        self,
        *,
        latest_summary: AssessmentSummary,
        recommended_terms: UnderwritingTerms,
        amount: float,
        tenure_months: int,
        cadence: RepaymentCadence,
    ) -> float:
        base_amount = recommended_terms.amount if recommended_terms.amount > 0 else 1.0
        base_installment = recommended_terms.estimated_installment
        amount_scale = amount / base_amount
        tenure_scale = recommended_terms.tenure_months / max(tenure_months, 1)
        installment = max(0.0, base_installment * amount_scale * tenure_scale)

        cadence_scale = {
            RepaymentCadence.DAILY: 1 / 30,
            RepaymentCadence.WEEKLY: 1 / 4.33,
            RepaymentCadence.MONTHLY: 1.0,
        }
        base_cadence_scale = cadence_scale.get(recommended_terms.repayment_cadence, 1.0)
        target_cadence_scale = cadence_scale.get(cadence, 1.0)
        if target_cadence_scale > 0:
            installment = installment * (target_cadence_scale / base_cadence_scale)

        fallback = latest_summary.estimated_installment or latest_summary.estimated_emi or 0.0
        return round(installment or fallback, 2)

    def _derive_policy_exception_flags(
        self,
        *,
        latest_summary: AssessmentSummary,
        recommended_terms: UnderwritingTerms,
        final_terms: UnderwritingTerms,
    ) -> list[str]:
        flags: list[str] = []

        if latest_summary.loan_range is not None:
            if (
                final_terms.amount < latest_summary.loan_range.low
                or final_terms.amount > latest_summary.loan_range.high
            ):
                flags.append("amount_outside_policy_range")

        pricing = latest_summary.pricing_recommendation
        if pricing is not None:
            if (
                final_terms.annual_interest_rate_pct < pricing.annual_interest_rate_band.low
                or final_terms.annual_interest_rate_pct > pricing.annual_interest_rate_band.high
            ):
                flags.append("interest_rate_outside_policy_band")
            if (
                final_terms.processing_fee_pct < pricing.processing_fee_band.low
                or final_terms.processing_fee_pct > pricing.processing_fee_band.high
            ):
                flags.append("processing_fee_outside_policy_band")

        if final_terms.amount != recommended_terms.amount:
            flags.append("amount_changed_from_recommendation")
        if final_terms.tenure_months != recommended_terms.tenure_months:
            flags.append("tenure_changed_from_recommendation")
        if final_terms.repayment_cadence != recommended_terms.repayment_cadence:
            flags.append("repayment_cadence_changed_from_recommendation")
        if final_terms.annual_interest_rate_pct != recommended_terms.annual_interest_rate_pct:
            flags.append("interest_rate_changed_from_recommendation")
        if final_terms.processing_fee_pct != recommended_terms.processing_fee_pct:
            flags.append("processing_fee_changed_from_recommendation")

        return flags

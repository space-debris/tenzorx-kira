"""
Loan lifecycle service for approval, disbursement, monitoring, and closure flows.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from models.output_schema import RiskBand
from models.platform_schema import (
    AssessmentCase,
    AuditAction,
    AuditEntityType,
    CaseStatus,
    LoanAccount,
    LoanAccountDetailResponse,
    LoanAccountStatus,
    LoanDecision,
    MonitoringRunRecord,
    RiskAlert,
    StatementUploadRecord,
)
from services.audit_service import AuditService
from storage.repository import PlatformRepository


def _build_statement_upload_record(upload) -> StatementUploadRecord:
    summary = upload.transaction_summary
    return StatementUploadRecord(
        id=str(upload.id),
        label=upload.file_name,
        status=upload.status.value if hasattr(upload.status, "value") else str(upload.status),
        created_at=upload.created_at,
        note=f"Uploaded {upload.file_name}",
        transaction_count=(
            (summary.credit_count + summary.debit_count)
            if summary is not None
            else 0
        ),
        inflow_total=summary.total_credits if summary is not None else 0.0,
        outflow_total=summary.total_debits if summary is not None else 0.0,
    )


def _build_monitoring_run_record(run) -> MonitoringRunRecord:
    suggestion = run.restructuring_suggestion
    utilization = {}
    if run.utilization is not None:
        utilization = {
            "supplier_inventory_pct": run.utilization.supplier_inventory_pct,
            "transfer_wallet_pct": run.utilization.transfer_wallet_pct,
            "personal_cash_pct": run.utilization.personal_cash_pct,
            "unknown_pct": run.utilization.unknown_pct,
        }
    return MonitoringRunRecord(
        id=str(run.id),
        created_at=run.created_at,
        current_risk_band=run.new_risk_band,
        inflow_change_ratio=run.inflow_velocity_change_pct or 0.0,
        stress_score=run.new_risk_score or 0.0,
        restructuring_recommendation=suggestion.rationale if suggestion is not None else None,
        utilization_breakdown=utilization,
    )


class LoanService:
    """Manage loan booking artifacts derived from approved lender cases."""

    def __init__(self, repository: PlatformRepository, audit_service: AuditService) -> None:
        self.repository = repository
        self.audit_service = audit_service

    def ensure_decision_for_case(
        self,
        case: AssessmentCase,
        actor_user_id: uuid.UUID,
        note: str | None = None,
    ) -> LoanDecision:
        existing = self.repository.get_latest_loan_decision(case.id)
        if existing is not None:
            return existing

        loan_range = case.latest_loan_range
        if loan_range is None:
            raise ValueError("Cannot approve a case without a loan recommendation")

        recommended_amount = round((loan_range.low + loan_range.high) / 2, 2)
        cadence = "weekly" if case.latest_risk_band in {RiskBand.MEDIUM, RiskBand.HIGH} else "monthly"
        pricing_rate = {
            RiskBand.LOW: 18.0,
            RiskBand.MEDIUM: 22.0,
            RiskBand.HIGH: 26.0,
            RiskBand.VERY_HIGH: 30.0,
            None: 22.0,
        }[case.latest_risk_band]

        decision = LoanDecision(
            org_id=case.org_id,
            case_id=case.id,
            assessment_session_id=case.latest_assessment_session_id,
            recommended_amount=recommended_amount,
            approved_amount=recommended_amount,
            recommended_tenure_months=12,
            approved_tenure_months=12,
            pricing_rate_annual=pricing_rate,
            processing_fee_rate=1.5,
            repayment_cadence=cadence,
            decision_reason=note or "Decision generated from latest assessment and policy guardrails.",
            created_by_user_id=actor_user_id,
        )
        self.repository.create_loan_decision(decision)
        self.audit_service.record_event(
            org_id=case.org_id,
            entity_type=AuditEntityType.LOAN,
            entity_id=decision.id,
            action=AuditAction.DECISION_RECORDED,
            description=f"Recorded loan decision for case {case.id}",
            actor_user_id=actor_user_id,
            metadata={
                "case_id": str(case.id),
                "approved_amount": decision.approved_amount,
                "repayment_cadence": decision.repayment_cadence,
            },
        )
        return decision

    def ensure_loan_account_for_case(
        self,
        case: AssessmentCase,
        actor_user_id: uuid.UUID,
    ) -> LoanAccount:
        existing = self.repository.get_loan_account_for_case(case.id)
        if existing is not None:
            return existing

        decision = self.ensure_decision_for_case(case, actor_user_id)
        loan_account = LoanAccount(
            org_id=case.org_id,
            case_id=case.id,
            kirana_id=case.kirana_id,
            assessment_session_id=case.latest_assessment_session_id,
            status=LoanAccountStatus.ACTIVE,
            principal_amount=decision.approved_amount,
            outstanding_principal=decision.approved_amount,
            tenure_months=decision.approved_tenure_months,
            annual_interest_rate_pct=decision.pricing_rate_annual,
            processing_fee_pct=decision.processing_fee_rate,
            repayment_cadence=decision.repayment_cadence,
            disbursed_at=datetime.utcnow(),
        )
        self.repository.create_loan_account(loan_account)
        self.audit_service.record_event(
            org_id=case.org_id,
            entity_type=AuditEntityType.LOAN,
            entity_id=loan_account.id,
            action=AuditAction.CREATED,
            description=f"Booked loan account for case {case.id}",
            actor_user_id=actor_user_id,
            metadata={
                "case_id": str(case.id),
                "principal_amount": loan_account.principal_amount,
            },
        )
        return loan_account

    def sync_loan_status(self, case: AssessmentCase) -> None:
        account = self.repository.get_loan_account_for_case(case.id)
        if account is None:
            return
        new_status = account.status
        if case.status == CaseStatus.CLOSED:
            new_status = LoanAccountStatus.CLOSED
        elif case.status == CaseStatus.RESTRUCTURED:
            new_status = LoanAccountStatus.RESTRUCTURED

        updated = account.model_copy(
            update={
                "status": new_status,
                "updated_at": datetime.utcnow(),
            }
        )
        self.repository.update_loan_account(updated)

    def get_loan_account_detail(self, case_id: uuid.UUID) -> LoanAccountDetailResponse:
        case = self.repository.get_case(case_id)
        if case is None:
            raise ValueError("Case not found")

        account = self.repository.get_loan_account_for_case(case_id)
        if account is None:
            raise ValueError("Loan account not found for case")

        kirana = self.repository.get_kirana(case.kirana_id)
        if kirana is None:
            raise ValueError("Kirana not found")

        decision = self.repository.get_latest_loan_decision(case_id)
        uploads = [
            _build_statement_upload_record(upload)
            for upload in self.repository.list_statement_uploads(case_id=case_id)
        ]
        monitoring_runs = [
            _build_monitoring_run_record(run)
            for run in self.repository.list_monitoring_runs(case_id=case_id)
        ]
        alerts = self.repository.list_alerts(case_id=case_id)
        audit_events = self.repository.list_audit_events(entity_id=case.id)
        audit_events.extend(self.repository.list_audit_events(entity_id=account.id))
        audit_events = sorted(
            {str(event.id): event for event in audit_events}.values(),
            key=lambda item: item.created_at,
            reverse=True,
        )

        return LoanAccountDetailResponse(
            loan_account=account,
            case=case,
            kirana=kirana,
            loan_decision=decision,
            statement_uploads=uploads,
            monitoring_runs=monitoring_runs,
            alerts=alerts,
            audit_events=audit_events,
        )

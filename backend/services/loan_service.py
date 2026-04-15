"""
KIRA — Loan Service

Phase 11: Loan lifecycle management.

Converts approved cases into booked loan accounts, manages loan status
transitions, and provides detailed loan views with associated monitoring
and statement data.

Owner: Orchestration Lead
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from models.output_schema import RepaymentCadence, RiskBand, ValueRange
from models.platform_schema import (
    AuditAction,
    AuditEntityType,
    BookLoanRequest,
    CaseStatus,
    LoanAccount,
    LoanAccountDetailResponse,
    LoanAccountStatus,
    LoanStatusUpdateRequest,
    UnderwritingTerms,
)
from services.audit_service import AuditService
from storage.repository import PlatformRepository

logger = logging.getLogger("kira.loan_service")


class LoanService:
    """Manages loan account creation, status changes, and detail retrieval."""

    def __init__(
        self,
        repository: PlatformRepository,
        audit_service: AuditService,
    ) -> None:
        self.repository = repository
        self.audit_service = audit_service

    # ------------------------------------------------------------------
    # Loan Booking
    # ------------------------------------------------------------------

    def book_loan(self, payload: BookLoanRequest) -> LoanAccountDetailResponse:
        """
        Create a LoanAccount from an approved case.

        The case must be in APPROVED or DISBURSED status and have a valid
        underwriting decision with final terms. The original assessment
        snapshot is frozen into the loan record for traceability.
        """
        case = self.repository.get_case(payload.case_id)
        if case is None:
            raise ValueError("Case not found")

        actor = self.repository.get_user(payload.actor_user_id)
        if actor is None or actor.org_id != case.org_id:
            raise ValueError("Actor is invalid for this organization")

        if case.status not in {CaseStatus.APPROVED, CaseStatus.DISBURSED}:
            raise ValueError(
                f"Case must be in APPROVED or DISBURSED status to book a loan, "
                f"currently {case.status.value}"
            )

        # Check for existing loan on this case
        existing = self.repository.list_loan_accounts(case_id=case.id)
        if existing:
            raise ValueError("A loan account already exists for this case")

        # Resolve underwriting terms
        decision = self.repository.get_latest_underwriting_decision(case.id)
        if decision is None or decision.final_terms is None:
            raise ValueError("Case has no finalized underwriting terms")

        terms: UnderwritingTerms = decision.final_terms
        now = payload.disbursement_date or datetime.utcnow()
        maturity = now + timedelta(days=int(terms.tenure_months * 30.44))

        # Resolve frozen assessment data
        original_risk_band = None
        original_revenue_range = None
        if case.latest_assessment_session_id:
            summary = self.repository.get_assessment_summary(
                case.latest_assessment_session_id
            )
            if summary:
                original_risk_band = summary.risk_band
                original_revenue_range = summary.revenue_range

        loan = LoanAccount(
            org_id=case.org_id,
            case_id=case.id,
            kirana_id=case.kirana_id,
            assessment_session_id=case.latest_assessment_session_id or uuid.uuid4(),
            status=LoanAccountStatus.ACTIVE,
            principal_amount=terms.amount,
            tenure_months=terms.tenure_months,
            repayment_cadence=terms.repayment_cadence,
            annual_interest_rate_pct=terms.annual_interest_rate_pct,
            processing_fee_pct=terms.processing_fee_pct,
            estimated_installment=terms.estimated_installment,
            disbursed_at=now,
            maturity_date=maturity,
            outstanding_principal=terms.amount,
            original_risk_band=original_risk_band,
            original_revenue_range=original_revenue_range,
            created_at=now,
            updated_at=now,
        )
        self.repository.create_loan_account(loan)

        # Transition case to DISBURSED if it was APPROVED
        if case.status == CaseStatus.APPROVED:
            updated_case = case.model_copy(
                update={
                    "status": CaseStatus.DISBURSED,
                    "updated_at": now,
                }
            )
            self.repository.update_case(updated_case)

        self.audit_service.record_event(
            org_id=case.org_id,
            entity_type=AuditEntityType.LOAN,
            entity_id=loan.id,
            action=AuditAction.LOAN_BOOKED,
            description=(
                f"Booked loan ₹{terms.amount:,.0f} for case {case.id} "
                f"({terms.tenure_months}m, {terms.repayment_cadence.value})"
            ),
            actor_user_id=payload.actor_user_id,
            metadata={
                "case_id": str(case.id),
                "principal": terms.amount,
                "tenure_months": terms.tenure_months,
                "cadence": terms.repayment_cadence.value,
                "rate": terms.annual_interest_rate_pct,
            },
        )

        logger.info(
            "Loan booked: loan_id=%s, case_id=%s, amount=₹%s",
            loan.id, case.id, f"{terms.amount:,.0f}",
        )
        return self.get_loan_detail(loan.id)

    # ------------------------------------------------------------------
    # Status Updates
    # ------------------------------------------------------------------

    def update_loan_status(
        self,
        loan_id: uuid.UUID,
        payload: LoanStatusUpdateRequest,
    ) -> LoanAccountDetailResponse:
        """Change the status of a loan account."""
        loan = self.repository.get_loan_account(loan_id)
        if loan is None:
            raise ValueError("Loan account not found")

        actor = self.repository.get_user(payload.actor_user_id)
        if actor is None or actor.org_id != loan.org_id:
            raise ValueError("Actor is invalid for this organization")

        now = datetime.utcnow()
        update: dict[str, Any] = {
            "status": payload.new_status,
            "updated_at": now,
        }
        if payload.days_past_due is not None:
            update["days_past_due"] = payload.days_past_due

        updated = loan.model_copy(update=update)
        self.repository.update_loan_account(updated)

        # If closing, also transition case
        if payload.new_status == LoanAccountStatus.CLOSED:
            case = self.repository.get_case(loan.case_id)
            if case and case.status != CaseStatus.CLOSED:
                self.repository.update_case(
                    case.model_copy(
                        update={"status": CaseStatus.CLOSED, "updated_at": now}
                    )
                )

        # If restructured, also transition case
        if payload.new_status == LoanAccountStatus.RESTRUCTURED:
            case = self.repository.get_case(loan.case_id)
            if case and case.status != CaseStatus.RESTRUCTURED:
                self.repository.update_case(
                    case.model_copy(
                        update={"status": CaseStatus.RESTRUCTURED, "updated_at": now}
                    )
                )

        self.audit_service.record_event(
            org_id=loan.org_id,
            entity_type=AuditEntityType.LOAN,
            entity_id=loan.id,
            action=AuditAction.LOAN_STATUS_CHANGED,
            description=(
                f"Changed loan status from {loan.status.value} to {payload.new_status.value}"
            ),
            actor_user_id=payload.actor_user_id,
            metadata={
                "previous_status": loan.status.value,
                "new_status": payload.new_status.value,
                "note": payload.note,
            },
        )

        logger.info(
            "Loan status updated: loan_id=%s, %s -> %s",
            loan_id, loan.status.value, payload.new_status.value,
        )
        return self.get_loan_detail(loan_id)

    # ------------------------------------------------------------------
    # Detail Views
    # ------------------------------------------------------------------

    def get_loan_detail(self, loan_id: uuid.UUID) -> LoanAccountDetailResponse:
        """Return full loan account detail with related entities."""
        loan = self.repository.get_loan_account(loan_id)
        if loan is None:
            raise ValueError("Loan account not found")

        case = self.repository.get_case(loan.case_id)
        if case is None:
            raise ValueError("Case not found for loan")

        kirana = self.repository.get_kirana(loan.kirana_id)
        if kirana is None:
            raise ValueError("Kirana not found for loan")

        statements = self.repository.list_statement_uploads(loan_id=loan.id)
        monitoring_runs = self.repository.list_monitoring_runs(loan_id=loan.id)
        alerts = self.repository.list_alerts(case_id=loan.case_id)

        audit_events = self.repository.list_audit_events(entity_id=loan.id)
        audit_events.extend(self.repository.list_audit_events(entity_id=case.id))
        audit_events = sorted(
            {str(e.id): e for e in audit_events}.values(),
            key=lambda e: e.created_at,
            reverse=True,
        )

        return LoanAccountDetailResponse(
            loan=loan,
            case=case,
            kirana=kirana,
            statement_uploads=statements,
            monitoring_runs=monitoring_runs,
            alerts=alerts,
            audit_events=list(audit_events),
        )

    def list_loans_for_org(
        self,
        org_id: uuid.UUID,
    ) -> list[LoanAccount]:
        """List all loan accounts for an organization."""
        org = self.repository.get_organization(org_id)
        if org is None:
            raise ValueError("Organization not found")
        return self.repository.list_loan_accounts(org_id=org_id)

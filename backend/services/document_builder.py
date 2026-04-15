"""
KIRA — Document Builder

Phase 13: Deterministic loan and case file generation.

Produces structured document bundles from assessment, underwriting,
and case data. Uses templates with inserted values rather than
free-form LLM generation for policy-critical fields.

Owner: Orchestration Lead
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from models.output_schema import RiskBand
from models.platform_schema import (
    AssessmentCase,
    AssessmentSummary,
    AuditEvent,
    KiranaProfile,
    LoanAccount,
    UnderwritingDecision,
)

logger = logging.getLogger("kira.document_builder")


# ---------------------------------------------------------------------------
# Document Models
# ---------------------------------------------------------------------------


class DocumentSection(BaseModel):
    """A single section within a generated document."""

    title: str
    content: str
    data: dict[str, Any] = Field(default_factory=dict)


class GeneratedDocument(BaseModel):
    """A generated document ready for rendering or export."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    document_type: str
    title: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    sections: list[DocumentSection] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_underwriting_summary(
    case: AssessmentCase,
    kirana: KiranaProfile,
    assessment: AssessmentSummary | None,
    decision: UnderwritingDecision | None,
) -> GeneratedDocument:
    """
    Generate a deterministic underwriting summary document.

    Includes: borrower profile, assessment results, risk analysis,
    loan recommendation, and underwriting terms.
    """
    sections: list[DocumentSection] = []

    # Section 1: Borrower Profile
    sections.append(DocumentSection(
        title="Borrower Profile",
        content=(
            f"Store Name: {kirana.store_name}\n"
            f"Owner: {kirana.owner_name}\n"
            f"Mobile: {kirana.owner_mobile}\n"
            f"Location: {kirana.location.locality or ''}, {kirana.location.district}, "
            f"{kirana.location.state} — {kirana.location.pin_code}\n"
            f"Onboarded: {kirana.created_at.strftime('%d %b %Y')}"
        ),
        data={
            "store_name": kirana.store_name,
            "owner_name": kirana.owner_name,
            "state": kirana.location.state,
            "district": kirana.location.district,
            "pin_code": kirana.location.pin_code,
        },
    ))

    # Section 2: Assessment Results
    if assessment:
        revenue_str = "N/A"
        if assessment.revenue_range:
            revenue_str = (
                f"₹{assessment.revenue_range.low:,.0f} — ₹{assessment.revenue_range.high:,.0f}"
            )
        sections.append(DocumentSection(
            title="Assessment Results",
            content=(
                f"Risk Band: {assessment.risk_band.value if assessment.risk_band else 'N/A'}\n"
                f"Risk Score: {assessment.risk_score:.2f}\n"
                f"Monthly Revenue Estimate: {revenue_str}\n"
                f"Eligible: {'Yes' if assessment.eligible else 'No'}\n"
                f"Fraud Flagged: {'Yes' if assessment.fraud_flagged else 'No'}\n"
                f"Completed: {assessment.completed_at.strftime('%d %b %Y %H:%M')}"
            ),
            data={
                "risk_band": assessment.risk_band.value if assessment.risk_band else None,
                "risk_score": assessment.risk_score,
                "eligible": assessment.eligible,
                "fraud_flagged": assessment.fraud_flagged,
            },
        ))

    # Section 3: Loan Recommendation
    if assessment and assessment.loan_range:
        sections.append(DocumentSection(
            title="Loan Recommendation",
            content=(
                f"Loan Range: ₹{assessment.loan_range.low:,.0f} — ₹{assessment.loan_range.high:,.0f}\n"
                f"Recommended Amount: ₹{assessment.recommended_amount:,.0f}\n"
                f"Suggested Tenure: {assessment.suggested_tenure_months or 'N/A'} months\n"
                f"EMI-to-Income Ratio: {assessment.emi_to_income_ratio or 'N/A'}\n"
                f"Repayment Cadence: {assessment.repayment_cadence.value if assessment.repayment_cadence else 'N/A'}"
            ),
            data={
                "loan_low": assessment.loan_range.low,
                "loan_high": assessment.loan_range.high,
                "recommended_amount": assessment.recommended_amount,
                "tenure_months": assessment.suggested_tenure_months,
            },
        ))

    # Section 4: Underwriting Decision
    if decision:
        terms = decision.final_terms
        sections.append(DocumentSection(
            title="Underwriting Decision",
            content=(
                f"Eligible: {'Yes' if decision.eligible else 'No'}\n"
                f"Has Override: {'Yes' if decision.has_override else 'No'}\n"
                f"Final Amount: ₹{terms.amount:,.0f}\n"
                f"Tenure: {terms.tenure_months} months\n"
                f"Cadence: {terms.repayment_cadence.value}\n"
                f"Annual Rate: {terms.annual_interest_rate_pct:.2f}%\n"
                f"Processing Fee: {terms.processing_fee_pct:.2f}%\n"
                f"Estimated Installment: ₹{terms.estimated_installment:,.0f}"
            ) if terms else "No finalized terms available.",
            data={
                "has_override": decision.has_override,
                "override_reason": decision.override_reason,
                "policy_flags": decision.policy_exception_flags,
            },
        ))

        if decision.has_override and decision.override_reason:
            sections.append(DocumentSection(
                title="Override Details",
                content=(
                    f"Reason: {decision.override_reason}\n"
                    f"Policy Exceptions: {', '.join(decision.policy_exception_flags) or 'None'}\n"
                    f"Overridden At: {decision.overridden_at.strftime('%d %b %Y %H:%M') if decision.overridden_at else 'N/A'}"
                ),
                data={"policy_exception_flags": decision.policy_exception_flags},
            ))

    # Section 5: Explanation Summary
    if assessment and assessment.explanation_summary:
        summary = assessment.explanation_summary
        strengths_str = "\n".join(f"  • {s}" for s in (summary.strengths or []))
        concerns_str = "\n".join(f"  • {c}" for c in (summary.concerns or []))
        sections.append(DocumentSection(
            title="Risk Narrative",
            content=(
                f"Overall: {summary.overall_narrative or 'N/A'}\n\n"
                f"Strengths:\n{strengths_str or '  None identified'}\n\n"
                f"Concerns:\n{concerns_str or '  None identified'}\n\n"
                f"Recommendation: {summary.recommendation or 'N/A'}"
            ),
            data={
                "strengths": summary.strengths,
                "concerns": summary.concerns,
            },
        ))

    return GeneratedDocument(
        document_type="underwriting_summary",
        title=f"Underwriting Summary — {kirana.store_name}",
        sections=sections,
        metadata={
            "case_id": str(case.id),
            "kirana_id": str(kirana.id),
            "case_status": case.status.value,
        },
    )


def build_sanction_note(
    case: AssessmentCase,
    kirana: KiranaProfile,
    decision: UnderwritingDecision | None,
    loan: LoanAccount | None = None,
) -> GeneratedDocument:
    """Generate a deterministic sanction note for loan approval."""
    sections: list[DocumentSection] = []

    sections.append(DocumentSection(
        title="Sanction Reference",
        content=(
            f"Case ID: {case.id}\n"
            f"Borrower: {kirana.store_name} ({kirana.owner_name})\n"
            f"Location: {kirana.location.district}, {kirana.location.state}\n"
            f"Date: {datetime.utcnow().strftime('%d %b %Y')}"
        ),
        data={"case_id": str(case.id)},
    ))

    if decision and decision.final_terms:
        terms = decision.final_terms
        sections.append(DocumentSection(
            title="Sanctioned Terms",
            content=(
                f"Amount: ₹{terms.amount:,.0f}\n"
                f"Tenure: {terms.tenure_months} months\n"
                f"Repayment: {terms.repayment_cadence.value}\n"
                f"Interest Rate: {terms.annual_interest_rate_pct:.2f}% p.a.\n"
                f"Processing Fee: {terms.processing_fee_pct:.2f}%\n"
                f"Installment: ₹{terms.estimated_installment:,.0f}"
            ),
            data={"amount": terms.amount, "tenure": terms.tenure_months},
        ))

    if decision and decision.has_override:
        sections.append(DocumentSection(
            title="Override Declaration",
            content=(
                f"This sanction includes officer override(s).\n"
                f"Reason: {decision.override_reason or 'Not specified'}\n"
                f"Policy Exceptions: {', '.join(decision.policy_exception_flags) or 'None'}"
            ),
            data={"policy_flags": decision.policy_exception_flags},
        ))

    if loan:
        sections.append(DocumentSection(
            title="Disbursement Record",
            content=(
                f"Loan ID: {loan.id}\n"
                f"Disbursed: {loan.disbursed_at.strftime('%d %b %Y') if loan.disbursed_at else 'Pending'}\n"
                f"Maturity: {loan.maturity_date.strftime('%d %b %Y') if loan.maturity_date else 'TBD'}"
            ),
            data={"loan_id": str(loan.id)},
        ))

    return GeneratedDocument(
        document_type="sanction_note",
        title=f"Sanction Note — {kirana.store_name}",
        sections=sections,
        metadata={"case_id": str(case.id)},
    )


def build_monitoring_summary(
    loan: LoanAccount,
    kirana: KiranaProfile,
    monitoring_runs: list | None = None,
) -> GeneratedDocument:
    """Generate a monitoring history summary document."""
    sections: list[DocumentSection] = []

    sections.append(DocumentSection(
        title="Loan Overview",
        content=(
            f"Loan ID: {loan.id}\n"
            f"Borrower: {kirana.store_name}\n"
            f"Principal: ₹{loan.principal_amount:,.0f}\n"
            f"Outstanding: ₹{(loan.outstanding_principal or 0):,.0f}\n"
            f"Status: {loan.status.value}\n"
            f"Days Past Due: {loan.days_past_due}"
        ),
        data={"loan_id": str(loan.id), "status": loan.status.value},
    ))

    if loan.utilization:
        sections.append(DocumentSection(
            title="Current Utilization",
            content=(
                f"Supplier/Inventory: {loan.utilization.supplier_inventory_pct:.1f}%\n"
                f"Transfer/Wallet: {loan.utilization.transfer_wallet_pct:.1f}%\n"
                f"Personal/Cash: {loan.utilization.personal_cash_pct:.1f}%\n"
                f"Unknown: {loan.utilization.unknown_pct:.1f}%\n"
                f"Diversion Risk: {loan.utilization.diversion_risk}"
            ),
            data={"diversion_risk": loan.utilization.diversion_risk},
        ))

    if monitoring_runs:
        run_lines = []
        for run in monitoring_runs[:10]:
            risk = run.new_risk_band.value if run.new_risk_band else "N/A"
            date = run.completed_at.strftime('%d %b %Y') if run.completed_at else "In progress"
            alerts = len(run.alerts_raised) if run.alerts_raised else 0
            run_lines.append(f"  [{date}] Risk: {risk}, Alerts: {alerts}, Status: {run.status.value}")

        sections.append(DocumentSection(
            title="Monitoring History",
            content="\n".join(run_lines) if run_lines else "No monitoring runs recorded.",
            data={"run_count": len(monitoring_runs)},
        ))

    return GeneratedDocument(
        document_type="monitoring_summary",
        title=f"Monitoring Summary — {kirana.store_name}",
        sections=sections,
        metadata={"loan_id": str(loan.id)},
    )

"""
Deterministic document bundle generation for case and loan files.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from models.platform_schema import DocumentBundle, DocumentBundleResponse
from storage.repository import PlatformRepository


def _monitoring_summary(run) -> dict:
    return {
        "created_at": run.created_at.isoformat(),
        "current_risk_band": run.new_risk_band.value if run.new_risk_band else None,
        "stress_score": run.new_risk_score or 0.0,
        "restructuring_recommendation": (
            run.restructuring_suggestion.rationale
            if run.restructuring_suggestion is not None
            else None
        ),
    }


class DocumentBuilder:
    """Build deterministic case and loan packet payloads."""

    def __init__(self, repository: PlatformRepository) -> None:
        self.repository = repository

    def build_case_bundle(
        self,
        case_id: uuid.UUID,
        generated_by_user_id: uuid.UUID | None = None,
    ) -> DocumentBundleResponse:
        case = self.repository.get_case(case_id)
        if case is None:
            raise ValueError("Case not found")
        kirana = self.repository.get_kirana(case.kirana_id)
        if kirana is None:
            raise ValueError("Kirana not found")

        decision = self.repository.get_latest_loan_decision(case_id)
        loan_account = self.repository.get_loan_account_for_case(case_id)
        monitoring_runs = self.repository.list_monitoring_runs(case_id=case_id)
        audit_events = self.repository.list_audit_events(entity_id=case_id)
        bundles = self.repository.list_document_bundles(case_id=case_id)
        if bundles:
            bundle = bundles[0]
        else:
            bundle = DocumentBundle(
                org_id=case.org_id,
                case_id=case.id,
                documents={
                    "underwriting_summary": "generated",
                    "sanction_note": "generated" if decision else "pending",
                    "decision_override_sheet": "generated" if decision and decision.override_reason else "not_required",
                    "monitoring_history_summary": "generated" if monitoring_runs else "pending",
                    "audit_event_export": "generated",
                },
                created_at=datetime.utcnow(),
                generated_by_user_id=generated_by_user_id,
                export_formats=["json", "pdf"],
            )
            self.repository.create_document_bundle(bundle)

        payload = {
            "underwriting_summary": {
                "case_id": str(case.id),
                "store_name": kirana.store_name,
                "status": case.status.value,
                "latest_risk_band": case.latest_risk_band.value if case.latest_risk_band else None,
                "loan_range": case.latest_loan_range.model_dump(mode="json") if case.latest_loan_range else None,
            },
            "sanction_note": {
                "approved_amount": decision.approved_amount if decision else None,
                "tenure_months": decision.approved_tenure_months if decision else None,
                "pricing_rate_annual": decision.pricing_rate_annual if decision else None,
                "repayment_cadence": decision.repayment_cadence if decision else None,
            },
            "decision_override_sheet": {
                "override_reason": decision.override_reason if decision else None,
                "decision_reason": decision.decision_reason if decision else None,
            },
            "monitoring_history_summary": [
                _monitoring_summary(run)
                for run in monitoring_runs
            ],
            "audit_event_export": [
                {
                    "created_at": event.created_at.isoformat(),
                    "action": event.action.value,
                    "description": event.description,
                    "actor_name": event.actor_name,
                }
                for event in audit_events
            ],
            "loan_account": loan_account.model_dump(mode="json") if loan_account else None,
        }
        return DocumentBundleResponse(bundle=bundle, payload=payload)

"""
Statement-driven monitoring and early-stress heuristics.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from models.output_schema import RiskBand
from models.platform_schema import (
    AlertSeverity,
    AlertStatus,
    AuditAction,
    AuditEntityType,
    CaseStatus,
    MonitoringRun,
    MonitoringRunRecord,
    RiskAlert,
    StatementUpload,
    StatementUploadCreateRequest,
    StatementUploadRecord,
    StatementUploadResponse,
)
from services.audit_service import AuditService
from services.loan_service import LoanService
from services.statement_parser import parse_statement_content
from storage.repository import PlatformRepository
from orchestration.enhanced_fraud import detect_longitudinal_fraud


class MonitoringService:
    """Parse fresh statements, create monitoring runs, and raise conservative alerts."""

    def __init__(
        self,
        repository: PlatformRepository,
        audit_service: AuditService,
        loan_service: LoanService,
    ) -> None:
        self.repository = repository
        self.audit_service = audit_service
        self.loan_service = loan_service

    def upload_statement(
        self,
        case_id: uuid.UUID,
        payload: StatementUploadCreateRequest,
    ) -> StatementUploadResponse:
        case = self.repository.get_case(case_id)
        if case is None:
            raise ValueError("Case not found")
        if case.status not in {CaseStatus.DISBURSED, CaseStatus.MONITORING, CaseStatus.RESTRUCTURED}:
            raise ValueError("Statements can only be uploaded for active loan cases")

        actor = self.repository.get_user(payload.actor_user_id)
        if actor is None or actor.org_id != case.org_id:
            raise ValueError("Actor is invalid for this organization")

        loan_account = self.loan_service.ensure_loan_account_for_case(case, payload.actor_user_id)
        parsed = parse_statement_content(payload.file_name, payload.content)
        upload = StatementUpload(
            org_id=case.org_id,
            case_id=case.id,
            loan_account_id=loan_account.id,
            uploaded_by_user_id=payload.actor_user_id,
            file_name=payload.file_name,
            file_type=payload.file_type,
            source_kind=payload.source_kind,
            parse_status=parsed["parse_status"],
            parse_confidence=parsed["parse_confidence"],
            transaction_count=parsed["transaction_count"],
            inflow_total=parsed["inflow_total"],
            outflow_total=parsed["outflow_total"],
            period_start=_parse_iso(parsed.get("period_start")),
            period_end=_parse_iso(parsed.get("period_end")),
            parsed_summary=self._build_parsed_summary(parsed["transactions"], parsed["inflow_total"], parsed["outflow_total"]),
        )
        self.repository.create_statement_upload(upload)
        self.audit_service.record_event(
            org_id=case.org_id,
            entity_type=AuditEntityType.CASE,
            entity_id=case.id,
            action=AuditAction.STATEMENT_UPLOADED,
            description=f"Uploaded statement {payload.file_name}",
            actor_user_id=payload.actor_user_id,
            metadata={
                "statement_upload_id": str(upload.id),
                "transaction_count": upload.transaction_count,
            },
        )

        monitoring_run, alerts = self._create_monitoring_run(case_id, upload)
        return StatementUploadResponse(
            statement_upload=StatementUploadRecord(
                id=str(upload.id),
                label=upload.file_name,
                status=upload.status.value if hasattr(upload.status, "value") else str(upload.status),
                created_at=upload.created_at,
                note=f"Uploaded {upload.file_name}",
                transaction_count=(upload.transaction_summary.credit_count + upload.transaction_summary.debit_count) if upload.transaction_summary else 0,
                inflow_total=upload.transaction_summary.total_credits if upload.transaction_summary else 0.0,
                outflow_total=upload.transaction_summary.total_debits if upload.transaction_summary else 0.0,
            ),
            monitoring_run=MonitoringRunRecord(
                id=str(monitoring_run.id),
                created_at=monitoring_run.created_at,
                current_risk_band=monitoring_run.current_risk_band,
                inflow_change_ratio=monitoring_run.inflow_change_ratio,
                stress_score=monitoring_run.stress_score,
                restructuring_recommendation=monitoring_run.restructuring_recommendation,
                utilization_breakdown=monitoring_run.utilization_breakdown,
            ),
            alerts=alerts,
        )

    def _create_monitoring_run(
        self,
        case_id: uuid.UUID,
        upload: StatementUpload,
    ) -> tuple[MonitoringRun, list[RiskAlert]]:
        case = self.repository.get_case(case_id)
        if case is None:
            raise ValueError("Case not found")

        previous_run = self.repository.get_latest_monitoring_run(case_id)
        baseline_inflow = previous_run.current_inflow_total if previous_run else (
            case.latest_loan_range.high if case.latest_loan_range else upload.inflow_total
        )
        if baseline_inflow <= 0:
            baseline_inflow = upload.inflow_total or 1.0

        inflow_change_ratio = round((upload.inflow_total - baseline_inflow) / baseline_inflow, 4)
        utilization = upload.parsed_summary.get("utilization_breakdown", {})
        cash_share = utilization.get("personal_or_cash_withdrawal_like", 0.0)
        stress_score = min(1.0, max(0.0, (cash_share * 0.6) + (max(0.0, -inflow_change_ratio) * 0.8)))
        current_risk = _risk_from_stress(case.latest_risk_band, stress_score)
        restructure = None
        if inflow_change_ratio <= -0.30:
            restructure = "Consider 1-2 month tenor extension and tighter statement refresh cadence."
        elif inflow_change_ratio <= -0.15:
            restructure = "Soft stress detected. Review collections and refresh in 14 days."

        alerts: list[RiskAlert] = []
        
        # Enhanced Fraud Detection Integration
        try:
            past_uploads = self.repository.list_statement_uploads(case_id=case_id)
            fraud_check = detect_longitudinal_fraud(upload.model_dump(), [u.model_dump() for u in past_uploads if u.id != upload.id])
            if fraud_check.get("is_flagged"):
                stress_score = min(1.0, stress_score + fraud_check.get("suspicion_score", 0))
                current_risk = _risk_from_stress(case.latest_risk_band, stress_score)
                for flag in fraud_check.get("flags", []):
                    alerts.append(
                        self.repository.create_alert(
                            RiskAlert(
                                org_id=case.org_id,
                                case_id=case.id,
                                kirana_id=case.kirana_id,
                                severity=AlertSeverity.CRITICAL,
                                status=AlertStatus.OPEN,
                                title="Behavioral Anomaly Detected",
                                description=f"Longitudinal fraud check flagged: {flag.replace('_', ' ').capitalize()}.",
                            )
                        )
                    )
        except Exception:
            pass # Fallback to normal flow if history unavailable
            
        if inflow_change_ratio <= -0.20:
            alerts.append(
                self.repository.create_alert(
                    RiskAlert(
                        org_id=case.org_id,
                        case_id=case.id,
                        kirana_id=case.kirana_id,
                        severity=AlertSeverity.WARNING if inflow_change_ratio > -0.35 else AlertSeverity.CRITICAL,
                        status=AlertStatus.OPEN,
                        title="Cash-flow deterioration detected",
                        description=f"Fresh statements show {abs(round(inflow_change_ratio * 100))}% lower inflows than the prior baseline.",
                    )
                )
            )
        if cash_share >= 0.35:
            alerts.append(
                self.repository.create_alert(
                    RiskAlert(
                        org_id=case.org_id,
                        case_id=case.id,
                        kirana_id=case.kirana_id,
                        severity=AlertSeverity.WARNING,
                        status=AlertStatus.OPEN,
                        title="Possible fund diversion pattern",
                        description="Personal transfer or cash-withdrawal share is unusually high for this cycle.",
                    )
                )
            )

        run = MonitoringRun(
            org_id=case.org_id,
            case_id=case.id,
            loan_account_id=upload.loan_account_id,
            statement_upload_id=upload.id,
            previous_risk_band=case.latest_risk_band,
            current_risk_band=current_risk,
            previous_inflow_total=baseline_inflow,
            current_inflow_total=upload.inflow_total,
            inflow_change_ratio=inflow_change_ratio,
            utilization_breakdown=utilization,
            stress_score=round(stress_score, 3),
            restructuring_recommendation=restructure,
            alerts_created=[alert.id for alert in alerts],
        )
        self.repository.create_monitoring_run(run)
        self.audit_service.record_event(
            org_id=case.org_id,
            entity_type=AuditEntityType.CASE,
            entity_id=case.id,
            action=AuditAction.MONITORING_RUN_COMPLETED,
            description=f"Completed monitoring run from statement {upload.file_name}",
            actor_user_id=upload.uploaded_by_user_id,
            metadata={
                "monitoring_run_id": str(run.id),
                "stress_score": run.stress_score,
                "current_risk_band": run.current_risk_band.value,
            },
        )
        return run, alerts

    def _build_parsed_summary(self, transactions: list[dict], inflow_total: float, outflow_total: float) -> dict:
        supplier = 0.0
        transfer = 0.0
        personal = 0.0
        unknown = 0.0
        for transaction in transactions:
            if transaction.get("type") != "debit":
                continue
            description = str(transaction.get("description", "")).lower()
            amount = float(transaction.get("amount", 0.0) or 0.0)
            if any(token in description for token in ("supplier", "wholesale", "inventory", "mart", "traders")):
                supplier += amount
            elif any(token in description for token in ("wallet", "upi", "transfer", "paytm", "phonepe", "gpay")):
                transfer += amount
            elif any(token in description for token in ("cash", "atm", "self", "personal")):
                personal += amount
            else:
                unknown += amount

        denominator = outflow_total if outflow_total > 0 else 1.0
        return {
            "utilization_breakdown": {
                "supplier_or_inventory_like": round(supplier / denominator, 3),
                "transfer_or_wallet_like": round(transfer / denominator, 3),
                "personal_or_cash_withdrawal_like": round(personal / denominator, 3),
                "unknown": round(unknown / denominator, 3),
            },
            "net_flow": round(inflow_total - outflow_total, 2),
        }


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def _risk_from_stress(previous_risk: RiskBand | None, stress_score: float) -> RiskBand:
    if stress_score >= 0.75:
        return RiskBand.VERY_HIGH
    if stress_score >= 0.45:
        return RiskBand.HIGH
    if stress_score >= 0.2:
        return RiskBand.MEDIUM
    return previous_risk or RiskBand.LOW

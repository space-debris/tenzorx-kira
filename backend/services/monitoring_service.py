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
    MonitoringRunStatus,
    RiskAlert,
    StatementUpload,
    StatementUploadCreateRequest,
    StatementUploadRecord,
    StatementUploadResponse,
    StatementUploadStatus,
    TransactionSummary,
    UtilizationBreakdown,
)
from orchestration.restructuring_advisor import assess_restructuring_need
from services.audit_service import AuditService
from services.loan_service import LoanService
from services.statement_parser import parse_statement_content
from storage.repository import PlatformRepository
from orchestration.enhanced_fraud import detect_longitudinal_fraud


def _build_statement_upload_record(upload: StatementUpload) -> StatementUploadRecord:
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


def _build_monitoring_run_record(run: MonitoringRun) -> MonitoringRunRecord:
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
        parsed = parse_statement_content(payload.file_name, payload.content, payload.file_type)
        period_days = max(0, int(parsed.get("period_days") or 0))
        upload_status = _derive_upload_status(parsed)
        avg_daily_balance = 0.0
        if period_days > 0:
            avg_daily_balance = round(
                max(parsed["inflow_total"] - parsed["outflow_total"], 0.0) / period_days * 7,
                2,
            )
        parsed_summary = self._build_parsed_summary(
            parsed["transactions"],
            parsed["inflow_total"],
            parsed["outflow_total"],
        )
        upload = StatementUpload(
            org_id=case.org_id,
            case_id=case.id,
            loan_id=loan_account.id,
            kirana_id=case.kirana_id,
            uploaded_by_user_id=payload.actor_user_id,
            status=upload_status,
            file_name=payload.file_name,
            file_type=payload.file_type,
            transaction_summary=TransactionSummary(
                total_credits=parsed["inflow_total"],
                total_debits=parsed["outflow_total"],
                credit_count=sum(1 for item in parsed["transactions"] if item.get("type") == "credit"),
                debit_count=sum(1 for item in parsed["transactions"] if item.get("type") == "debit"),
                avg_daily_balance=avg_daily_balance,
                period_days=period_days,
                start_date=_parse_iso(parsed.get("period_start")),
                end_date=_parse_iso(parsed.get("period_end")),
            ),
            parse_error=None if upload_status == StatementUploadStatus.PARSED else (parsed.get("summary") or parsed["parse_status"]),
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
                "transaction_count": upload.transaction_summary.credit_count + upload.transaction_summary.debit_count
                if upload.transaction_summary is not None
                else 0,
            },
        )

        monitoring_run, alerts = self._create_monitoring_run(case_id, loan_account, upload, parsed_summary)
        return StatementUploadResponse(
            statement_upload=_build_statement_upload_record(upload),
            monitoring_run=_build_monitoring_run_record(monitoring_run),
            alerts=alerts,
        )

    def _create_monitoring_run(
        self,
        case_id: uuid.UUID,
        loan_account,
        upload: StatementUpload,
        parsed_summary: dict,
    ) -> tuple[MonitoringRun, list[RiskAlert]]:
        case = self.repository.get_case(case_id)
        if case is None:
            raise ValueError("Case not found")

        previous_run = self.repository.get_latest_monitoring_run(case_id)
        previous_uploads = [
            existing
            for existing in self.repository.list_statement_uploads(case_id=case_id)
            if existing.id != upload.id
        ]
        previous_summary = previous_uploads[0].transaction_summary if previous_uploads else None
        latest_summary = (
            self.repository.get_assessment_summary(case.latest_assessment_session_id)
            if case.latest_assessment_session_id is not None
            else None
        )
        kirana = self.repository.get_kirana(case.kirana_id)
        upload_inflow_total = upload.transaction_summary.total_credits if upload.transaction_summary is not None else 0.0
        baseline_inflow, baseline_source = _resolve_baseline_inflow(
            case=case,
            previous_run=previous_run,
            latest_summary=latest_summary,
            kirana=kirana,
            current_inflow_total=upload_inflow_total,
        )

        inflow_change_ratio = round((upload_inflow_total - baseline_inflow) / baseline_inflow, 4)
        utilization = parsed_summary.get("utilization_breakdown", {})
        cash_share = utilization.get("personal_or_cash_withdrawal_like", 0.0)
        stress_score = min(1.0, max(0.0, (cash_share * 0.6) + (max(0.0, -inflow_change_ratio) * 0.8)))
        current_risk = _risk_from_stress(case.latest_risk_band, stress_score)
        current_summary = upload.transaction_summary
        if (
            previous_summary is None
            and current_summary is not None
            and baseline_inflow > 0
        ):
            previous_summary = TransactionSummary(
                total_credits=baseline_inflow,
                total_debits=current_summary.total_debits,
                credit_count=max(current_summary.credit_count, 1),
                debit_count=current_summary.debit_count,
                avg_daily_balance=current_summary.avg_daily_balance,
                period_days=max(current_summary.period_days, 30),
            )
        utilization_breakdown = _build_utilization_breakdown(utilization)
        restructuring_suggestion = assess_restructuring_need(
            loan=loan_account,
            current_summary=current_summary,
            previous_summary=previous_summary,
            utilization=utilization_breakdown,
        )

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
                        description=_build_inflow_alert_description(inflow_change_ratio, baseline_source),
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
            loan_id=upload.loan_id,
            kirana_id=upload.kirana_id,
            status=MonitoringRunStatus.COMPLETED,
            statement_upload_id=upload.id,
            previous_risk_band=case.latest_risk_band,
            new_risk_band=current_risk,
            new_risk_score=round(stress_score, 3),
            inflow_velocity_change_pct=inflow_change_ratio,
            utilization=utilization_breakdown,
            alerts_raised=[str(alert.id) for alert in alerts],
            restructuring_suggestion=restructuring_suggestion,
            run_notes=(
                f"baseline_inflow={baseline_inflow:.2f};"
                f"baseline_source={baseline_source};"
                f"current_inflow={upload_inflow_total:.2f}"
            ),
            completed_at=datetime.utcnow(),
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
                "stress_score": run.new_risk_score,
                "current_risk_band": run.new_risk_band.value if run.new_risk_band is not None else None,
                "restructuring_suggestion": (
                    restructuring_suggestion.rationale
                    if restructuring_suggestion is not None
                    else None
                ),
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


def _derive_upload_status(parsed: dict) -> StatementUploadStatus:
    if parsed.get("transaction_count", 0) > 0 or float(parsed.get("inflow_total", 0.0) or 0.0) > 0:
        return StatementUploadStatus.PARSED
    return StatementUploadStatus.FAILED


def previous_run_metadata_inflow(run: MonitoringRun | None) -> float | None:
    if run is None or not run.run_notes:
        return None
    for part in run.run_notes.split(";"):
        if part.startswith("current_inflow="):
            try:
                return float(part.split("=", 1)[1])
            except ValueError:
                return None
    return None


def _resolve_baseline_inflow(
    *,
    case,
    previous_run: MonitoringRun | None,
    latest_summary,
    kirana,
    current_inflow_total: float,
) -> tuple[float, str]:
    previous_inflow = previous_run_metadata_inflow(previous_run)
    if previous_inflow and previous_inflow > 0:
        return previous_inflow, "prior_statement_cycle"

    metadata_hint = None
    if kirana is not None:
        metadata_hint = kirana.metadata.get("monthly_revenue_hint")
    if metadata_hint:
        try:
            metadata_hint = float(metadata_hint)
        except (TypeError, ValueError):
            metadata_hint = None
    if metadata_hint and metadata_hint > 0:
        return metadata_hint, "statement_revenue_hint"

    if latest_summary is not None and latest_summary.revenue_range is not None:
        midpoint = (latest_summary.revenue_range.low + latest_summary.revenue_range.high) / 2
        if midpoint > 0:
            return midpoint, "assessment_revenue_midpoint"

    fallback = current_inflow_total or 1.0
    return fallback, "current_statement"


def _build_inflow_alert_description(inflow_change_ratio: float, baseline_source: str) -> str:
    rounded_drop = min(95, abs(round(inflow_change_ratio * 100)))
    source_label = {
        "prior_statement_cycle": "the prior statement cycle",
        "statement_revenue_hint": "the uploaded monthly revenue benchmark",
        "assessment_revenue_midpoint": "the assessment revenue benchmark",
        "current_statement": "the working baseline",
    }.get(baseline_source, "the working baseline")
    return f"Fresh statements are about {rounded_drop}% below {source_label}."


def _build_utilization_breakdown(utilization: dict[str, float]) -> UtilizationBreakdown:
    return UtilizationBreakdown(
        supplier_inventory_pct=round(utilization.get("supplier_or_inventory_like", 0.0) * 100, 2),
        transfer_wallet_pct=round(utilization.get("transfer_or_wallet_like", 0.0) * 100, 2),
        personal_cash_pct=round(utilization.get("personal_or_cash_withdrawal_like", 0.0) * 100, 2),
        unknown_pct=round(utilization.get("unknown", 0.0) * 100, 2),
        flags=[],
        diversion_risk="high" if utilization.get("personal_or_cash_withdrawal_like", 0.0) >= 0.35 else "low",
    )


def _risk_from_stress(previous_risk: RiskBand | None, stress_score: float) -> RiskBand:
    if stress_score >= 0.75:
        return RiskBand.VERY_HIGH
    if stress_score >= 0.45:
        return RiskBand.HIGH
    if stress_score >= 0.2:
        return RiskBand.MEDIUM
    return previous_risk or RiskBand.LOW

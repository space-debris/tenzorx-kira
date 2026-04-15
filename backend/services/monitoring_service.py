"""
KIRA — Monitoring Service

Phase 11: Scheduled or manual re-assessment pipeline.

Orchestrates the full monitoring cycle:
  1. Accept a fresh statement upload
  2. Parse transaction data
  3. Track utilization patterns
  4. Re-score risk using latest observations
  5. Detect stress and suggest restructuring
  6. Raise alerts for deteriorating patterns

Each monitoring run is recorded separately from the original
underwriting run for traceability.

Owner: Orchestration Lead
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from models.output_schema import RiskBand
from models.platform_schema import (
    AlertSeverity,
    AlertStatus,
    AuditAction,
    AuditEntityType,
    CaseStatus,
    LoanAccount,
    LoanAccountStatus,
    MonitoringRun,
    MonitoringRunStatus,
    RiskAlert,
    StatementUpload,
    StatementUploadStatus,
    TransactionSummary,
)
from orchestration.restructuring_advisor import (
    assess_restructuring_need,
    generate_stress_alerts,
)
from orchestration.utilization_tracker import classify_utilization
from services.audit_service import AuditService
from services.statement_parser import parse_statement
from storage.repository import PlatformRepository

logger = logging.getLogger("kira.monitoring_service")


class MonitoringService:
    """Orchestrates post-disbursement monitoring cycles."""

    def __init__(
        self,
        repository: PlatformRepository,
        audit_service: AuditService,
    ) -> None:
        self.repository = repository
        self.audit_service = audit_service

    # ------------------------------------------------------------------
    # Statement Upload
    # ------------------------------------------------------------------

    def upload_statement(
        self,
        loan_id: uuid.UUID,
        file_name: str,
        file_type: str,
        file_content: bytes,
        uploaded_by_user_id: uuid.UUID | None = None,
    ) -> StatementUpload:
        """
        Accept and parse a fresh bank/UPI statement for a loan.

        Creates a StatementUpload record, parses the file content,
        and updates the record with parsed results or error.

        Args:
            loan_id: The loan account to attach the statement to.
            file_name: Original file name.
            file_type: File type (pdf, csv).
            file_content: Raw file bytes.
            uploaded_by_user_id: User who performed the upload.

        Returns:
            StatementUpload: The created and parsed record.
        """
        loan = self.repository.get_loan_account(loan_id)
        if loan is None:
            raise ValueError("Loan account not found")

        now = datetime.utcnow()
        upload = StatementUpload(
            org_id=loan.org_id,
            case_id=loan.case_id,
            loan_id=loan.id,
            kirana_id=loan.kirana_id,
            status=StatementUploadStatus.PARSING,
            file_name=file_name,
            file_type=file_type.lower().strip("."),
            file_size_bytes=len(file_content),
            uploaded_by_user_id=uploaded_by_user_id,
            created_at=now,
            updated_at=now,
        )

        # Parse
        parsed_upload = parse_statement(upload, file_content)
        self.repository.create_statement_upload(parsed_upload)

        self.audit_service.record_event(
            org_id=loan.org_id,
            entity_type=AuditEntityType.LOAN,
            entity_id=loan.id,
            action=AuditAction.STATEMENT_UPLOADED,
            description=(
                f"Statement '{file_name}' uploaded and "
                f"{'parsed successfully' if parsed_upload.status == StatementUploadStatus.PARSED else 'parse failed'}"
            ),
            actor_user_id=uploaded_by_user_id,
            metadata={
                "file_name": file_name,
                "file_type": file_type,
                "status": parsed_upload.status.value,
                "file_size": len(file_content),
            },
        )

        logger.info(
            "Statement uploaded for loan %s: %s (%s)",
            loan_id, file_name, parsed_upload.status.value,
        )
        return parsed_upload

    # ------------------------------------------------------------------
    # Monitoring Run
    # ------------------------------------------------------------------

    def run_monitoring_cycle(
        self,
        loan_id: uuid.UUID,
        statement_upload_id: uuid.UUID | None = None,
        actor_user_id: uuid.UUID | None = None,
    ) -> MonitoringRun:
        """
        Execute a full monitoring re-assessment cycle for a loan.

        Steps:
        1. Resolve the latest statement data
        2. Classify utilization
        3. Re-score risk
        4. Check for restructuring need
        5. Raise alerts if applicable

        Args:
            loan_id: Target loan account.
            statement_upload_id: Specific statement to use (or latest if None).
            actor_user_id: Who triggered the run.

        Returns:
            MonitoringRun: The completed monitoring run record.
        """
        loan = self.repository.get_loan_account(loan_id)
        if loan is None:
            raise ValueError("Loan account not found")

        now = datetime.utcnow()

        # Create the monitoring run
        run = MonitoringRun(
            org_id=loan.org_id,
            case_id=loan.case_id,
            loan_id=loan.id,
            kirana_id=loan.kirana_id,
            status=MonitoringRunStatus.RUNNING,
            statement_upload_id=statement_upload_id,
            previous_risk_band=loan.original_risk_band,
            created_at=now,
            updated_at=now,
        )

        self.audit_service.record_event(
            org_id=loan.org_id,
            entity_type=AuditEntityType.LOAN,
            entity_id=loan.id,
            action=AuditAction.MONITORING_RUN_STARTED,
            description=f"Monitoring re-assessment cycle started",
            actor_user_id=actor_user_id,
            metadata={"run_id": str(run.id)},
        )

        try:
            # Step 1: Resolve statement data
            current_summary = self._resolve_statement_summary(
                loan, statement_upload_id,
            )
            previous_summary = self._resolve_previous_summary(loan)

            # Step 2: Classify utilization
            utilization = classify_utilization(current_summary)

            # Step 3: Re-score risk
            new_risk_band, new_risk_score = self._rescore_risk(
                loan, current_summary, previous_summary, utilization,
            )

            # Step 4: Compute inflow velocity change
            inflow_change = self._compute_inflow_change(
                current_summary, previous_summary,
            )

            # Step 5: Check restructuring need
            restructuring = assess_restructuring_need(
                loan=loan,
                current_summary=current_summary,
                previous_summary=previous_summary,
                utilization=utilization,
                monitoring_run=run,
            )

            # Step 6: Generate stress alerts
            alert_descriptions = generate_stress_alerts(
                loan, current_summary, previous_summary,
            )

            # Persist alerts
            alert_ids: list[str] = []
            for alert_desc in alert_descriptions:
                severity = (
                    AlertSeverity.CRITICAL
                    if "critical" in alert_desc.lower() or "immediate" in alert_desc.lower()
                    else AlertSeverity.WARNING
                )
                alert = RiskAlert(
                    org_id=loan.org_id,
                    case_id=loan.case_id,
                    kirana_id=loan.kirana_id,
                    severity=severity,
                    status=AlertStatus.OPEN,
                    title=alert_desc[:80],
                    description=alert_desc,
                    created_at=now,
                    updated_at=now,
                )
                self.repository.create_alert(alert)
                alert_ids.append(alert_desc[:80])

                self.audit_service.record_event(
                    org_id=loan.org_id,
                    entity_type=AuditEntityType.ALERT,
                    entity_id=alert.id,
                    action=AuditAction.ALERT_RAISED,
                    description=f"Alert raised: {alert_desc[:120]}",
                    actor_user_id=actor_user_id,
                    metadata={
                        "loan_id": str(loan.id),
                        "severity": severity.value,
                    },
                )

            # Update loan with latest utilization
            updated_loan = loan.model_copy(
                update={
                    "utilization": utilization,
                    "updated_at": now,
                }
            )
            self.repository.update_loan_account(updated_loan)

            # If case is DISBURSED, transition to MONITORING
            case = self.repository.get_case(loan.case_id)
            if case and case.status == CaseStatus.DISBURSED:
                self.repository.update_case(
                    case.model_copy(
                        update={"status": CaseStatus.MONITORING, "updated_at": now}
                    )
                )

            # Complete the run
            completed_run = run.model_copy(
                update={
                    "status": MonitoringRunStatus.COMPLETED,
                    "new_risk_band": new_risk_band,
                    "new_risk_score": new_risk_score,
                    "inflow_velocity_change_pct": inflow_change,
                    "utilization": utilization,
                    "alerts_raised": alert_ids,
                    "restructuring_suggestion": restructuring,
                    "completed_at": now,
                    "updated_at": now,
                }
            )
            self.repository.create_monitoring_run(completed_run)

            if restructuring:
                self.audit_service.record_event(
                    org_id=loan.org_id,
                    entity_type=AuditEntityType.LOAN,
                    entity_id=loan.id,
                    action=AuditAction.RESTRUCTURING_SUGGESTED,
                    description=f"Restructuring suggestion: {restructuring.suggestion_type}",
                    actor_user_id=actor_user_id,
                    metadata={
                        "suggestion_type": restructuring.suggestion_type,
                        "trigger": restructuring.trigger[:200],
                    },
                )

            self.audit_service.record_event(
                org_id=loan.org_id,
                entity_type=AuditEntityType.LOAN,
                entity_id=loan.id,
                action=AuditAction.MONITORING_RUN_COMPLETED,
                description=(
                    f"Monitoring cycle completed: risk={new_risk_band.value if new_risk_band else 'N/A'}, "
                    f"alerts={len(alert_ids)}"
                ),
                actor_user_id=actor_user_id,
                metadata={
                    "run_id": str(completed_run.id),
                    "new_risk_band": new_risk_band.value if new_risk_band else None,
                    "alerts_count": len(alert_ids),
                },
            )

            logger.info(
                "Monitoring completed for loan %s: risk=%s, alerts=%d",
                loan_id,
                new_risk_band.value if new_risk_band else "N/A",
                len(alert_ids),
            )

            return completed_run

        except Exception as exc:
            failed_run = run.model_copy(
                update={
                    "status": MonitoringRunStatus.FAILED,
                    "run_notes": f"Run failed: {str(exc)[:500]}",
                    "updated_at": datetime.utcnow(),
                }
            )
            self.repository.create_monitoring_run(failed_run)
            logger.error("Monitoring run failed for loan %s: %s", loan_id, exc)
            raise

    # ------------------------------------------------------------------
    # List Runs
    # ------------------------------------------------------------------

    def list_monitoring_runs(
        self,
        loan_id: uuid.UUID,
    ) -> list[MonitoringRun]:
        """List monitoring runs for a loan."""
        return self.repository.list_monitoring_runs(loan_id=loan_id)

    def list_statement_uploads(
        self,
        loan_id: uuid.UUID,
    ) -> list[StatementUpload]:
        """List statement uploads for a loan."""
        return self.repository.list_statement_uploads(loan_id=loan_id)

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _resolve_statement_summary(
        self,
        loan: LoanAccount,
        statement_upload_id: uuid.UUID | None,
    ) -> TransactionSummary | None:
        """Find the latest parsed statement summary for this loan."""
        if statement_upload_id:
            uploads = self.repository.list_statement_uploads(loan_id=loan.id)
            for upload in uploads:
                if upload.id == statement_upload_id and upload.transaction_summary:
                    return upload.transaction_summary

        # Fall back to most recent parsed upload
        uploads = self.repository.list_statement_uploads(loan_id=loan.id)
        for upload in uploads:
            if upload.status == StatementUploadStatus.PARSED and upload.transaction_summary:
                return upload.transaction_summary

        return None

    def _resolve_previous_summary(
        self,
        loan: LoanAccount,
    ) -> TransactionSummary | None:
        """Find the previous monitoring run's statement data for comparison."""
        runs = self.repository.list_monitoring_runs(loan_id=loan.id)
        for run in runs:
            if run.status == MonitoringRunStatus.COMPLETED and run.utilization:
                # Reconstruct from last known state
                uploads = self.repository.list_statement_uploads(loan_id=loan.id)
                for upload in uploads:
                    if (
                        upload.id == run.statement_upload_id
                        and upload.transaction_summary
                    ):
                        return upload.transaction_summary

        return None

    def _rescore_risk(
        self,
        loan: LoanAccount,
        current_summary: TransactionSummary | None,
        previous_summary: TransactionSummary | None,
        utilization: Any,
    ) -> tuple[RiskBand | None, float | None]:
        """
        Re-score risk based on latest statement data.

        Uses a simplified scoring model that adjusts the original risk
        band based on observed payment behavior and cash-flow trends.
        """
        base_band = loan.original_risk_band or RiskBand.MEDIUM
        base_score = {
            RiskBand.LOW: 0.25,
            RiskBand.MEDIUM: 0.45,
            RiskBand.HIGH: 0.65,
            RiskBand.VERY_HIGH: 0.85,
        }.get(base_band, 0.45)

        score_adj = 0.0

        # DPD impact
        if loan.days_past_due >= 30:
            score_adj += 0.2
        elif loan.days_past_due >= 15:
            score_adj += 0.1

        # Inflow velocity impact
        inflow_change = self._compute_inflow_change(current_summary, previous_summary)
        if inflow_change is not None:
            if inflow_change <= -30:
                score_adj += 0.15
            elif inflow_change <= -15:
                score_adj += 0.08
            elif inflow_change >= 15:
                score_adj -= 0.05

        # Utilization impact
        if utilization and hasattr(utilization, "diversion_risk"):
            if utilization.diversion_risk == "high":
                score_adj += 0.1
            elif utilization.diversion_risk == "medium":
                score_adj += 0.05

        # Balance adequacy
        if current_summary and loan.estimated_installment > 0:
            ratio = current_summary.avg_daily_balance / loan.estimated_installment
            if ratio < 1.0:
                score_adj += 0.1
            elif ratio > 3.0:
                score_adj -= 0.05

        final_score = max(0.0, min(1.0, base_score + score_adj))

        # Map score to band
        if final_score >= 0.75:
            new_band = RiskBand.VERY_HIGH
        elif final_score >= 0.55:
            new_band = RiskBand.HIGH
        elif final_score >= 0.35:
            new_band = RiskBand.MEDIUM
        else:
            new_band = RiskBand.LOW

        return new_band, round(final_score, 3)

    def _compute_inflow_change(
        self,
        current: TransactionSummary | None,
        previous: TransactionSummary | None,
    ) -> float | None:
        """Compute percentage change in daily credit inflow."""
        if not current or not previous:
            return None

        curr_days = max(1, current.period_days)
        prev_days = max(1, previous.period_days)

        curr_velocity = current.total_credits / curr_days
        prev_velocity = previous.total_credits / prev_days

        if prev_velocity <= 0:
            return None

        return round(((curr_velocity - prev_velocity) / prev_velocity) * 100, 2)

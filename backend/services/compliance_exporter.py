"""
KIRA — Compliance Exporter

Phase 13: Export audit and reporting bundles.

Produces machine-readable audit logs, case file packets, and
compliance-ready exports. All exports are deterministic and
do not depend on live model calls.

Owner: Orchestration Lead
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from models.platform_schema import (
    AuditAction,
    AuditEvent,
    AssessmentCase,
    KiranaProfile,
    LoanAccount,
)
from services.audit_service import AuditService
from services.document_builder import (
    GeneratedDocument,
    build_monitoring_summary,
    build_sanction_note,
    build_underwriting_summary,
)
from storage.repository import PlatformRepository

logger = logging.getLogger("kira.compliance_exporter")


# ---------------------------------------------------------------------------
# Export Models
# ---------------------------------------------------------------------------


class AuditExportEntry(BaseModel):
    """A single audit event in export-friendly format."""

    event_id: str
    timestamp: str
    entity_type: str
    entity_id: str
    action: str
    description: str
    actor: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditExportBundle(BaseModel):
    """Exportable bundle of audit events."""

    export_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    exported_at: datetime = Field(default_factory=datetime.utcnow)
    org_id: str
    total_events: int = 0
    events: list[AuditExportEntry] = Field(default_factory=list)
    filters_applied: dict[str, str] = Field(default_factory=dict)


class CaseFilePacket(BaseModel):
    """Complete case file bundle for compliance."""

    packet_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    case_id: str
    kirana_name: str
    documents: list[GeneratedDocument] = Field(default_factory=list)
    audit_bundle: AuditExportBundle | None = None


class ComplianceReport(BaseModel):
    """Summary compliance report for the organization."""

    report_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    org_id: str
    org_name: str
    total_cases: int = 0
    total_loans: int = 0
    cases_with_overrides: int = 0
    override_rate_pct: float = 0.0
    total_audit_events: int = 0
    policy_exceptions: list[dict[str, Any]] = Field(default_factory=list)
    high_risk_loans: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class ComplianceExporter:
    """Produces compliance-ready export bundles."""

    def __init__(self, repository: PlatformRepository) -> None:
        self.repository = repository

    # ------------------------------------------------------------------
    # Audit Export
    # ------------------------------------------------------------------

    def export_audit_events(
        self,
        org_id: uuid.UUID,
        entity_id: uuid.UUID | None = None,
        action_filter: str | None = None,
        limit: int = 500,
    ) -> AuditExportBundle:
        """
        Export audit events as a structured bundle.

        Filters can narrow by entity or action type. All exports
        include full event metadata for compliance traceability.
        """
        events = self.repository.list_audit_events(org_id=org_id, entity_id=entity_id)

        if action_filter:
            events = [e for e in events if e.action.value == action_filter]

        events = events[:limit]

        # Resolve actor names
        user_cache: dict[str, str] = {}
        for user in self.repository.list_users(org_id):
            user_cache[str(user.id)] = user.full_name

        entries = []
        for event in events:
            actor_name = "system"
            if hasattr(event, "actor_name") and event.actor_name:
                actor_name = event.actor_name
            elif hasattr(event, "actor_user_id") and event.actor_user_id:
                actor_name = user_cache.get(str(event.actor_user_id), str(event.actor_user_id))

            entries.append(AuditExportEntry(
                event_id=str(event.id),
                timestamp=event.created_at.isoformat(),
                entity_type=event.entity_type.value,
                entity_id=str(event.entity_id),
                action=event.action.value,
                description=event.description,
                actor=actor_name,
                metadata=event.metadata or {},
            ))

        filters = {}
        if entity_id:
            filters["entity_id"] = str(entity_id)
        if action_filter:
            filters["action"] = action_filter

        logger.info("Audit export: %d events for org %s", len(entries), org_id)

        return AuditExportBundle(
            org_id=str(org_id),
            total_events=len(entries),
            events=entries,
            filters_applied=filters,
        )

    # ------------------------------------------------------------------
    # Case File Packet
    # ------------------------------------------------------------------

    def generate_case_file_packet(
        self,
        case_id: uuid.UUID,
    ) -> CaseFilePacket:
        """
        Generate a complete loan file packet for a case.

        Includes underwriting summary, sanction note, monitoring
        summary (if loan exists), and audit trail.
        """
        case = self.repository.get_case(case_id)
        if case is None:
            raise ValueError("Case not found")

        kirana = self.repository.get_kirana(case.kirana_id)
        if kirana is None:
            raise ValueError("Kirana not found for case")

        # Resolve assessment
        assessment = None
        if case.latest_assessment_session_id:
            assessment = self.repository.get_assessment_summary(
                case.latest_assessment_session_id
            )

        # Resolve underwriting decision
        decision = self.repository.get_latest_underwriting_decision(case.id)

        # Resolve loan
        loans = self.repository.list_loan_accounts(case_id=case.id)
        loan = loans[0] if loans else None

        documents: list[GeneratedDocument] = []

        # 1. Underwriting Summary
        documents.append(
            build_underwriting_summary(case, kirana, assessment, decision)
        )

        # 2. Sanction Note
        documents.append(
            build_sanction_note(case, kirana, decision, loan)
        )

        # 3. Monitoring Summary (if loan exists)
        if loan:
            monitoring_runs = self.repository.list_monitoring_runs(loan_id=loan.id)
            documents.append(
                build_monitoring_summary(loan, kirana, monitoring_runs)
            )

        # 4. Audit trail
        audit_bundle = self.export_audit_events(
            org_id=case.org_id,
            entity_id=case.id,
        )

        logger.info(
            "Case file packet generated: case=%s, docs=%d",
            case_id, len(documents),
        )

        return CaseFilePacket(
            case_id=str(case.id),
            kirana_name=kirana.store_name,
            documents=documents,
            audit_bundle=audit_bundle,
        )

    # ------------------------------------------------------------------
    # Compliance Report
    # ------------------------------------------------------------------

    def generate_compliance_report(
        self,
        org_id: uuid.UUID,
    ) -> ComplianceReport:
        """
        Generate an organization-level compliance report.

        Summarizes override activity, policy exceptions, high-risk
        exposures, and audit coverage.
        """
        org = self.repository.get_organization(org_id)
        if org is None:
            raise ValueError("Organization not found")

        cases = self.repository.list_cases(org_id)
        loans = self.repository.list_loan_accounts(org_id=org_id)
        decisions = self.repository.list_underwriting_decisions()
        org_decisions = [d for d in decisions if d.org_id == org_id]
        audit_events = self.repository.list_audit_events(org_id=org_id)
        kiranas = self.repository.list_kiranas(org_id)
        kirana_map = {str(k.id): k for k in kiranas}

        # Override analysis
        overridden = [d for d in org_decisions if d.has_override]
        cases_with_overrides = len({str(d.case_id) for d in overridden})
        override_rate = (
            cases_with_overrides / max(1, len(cases)) * 100
        )

        # Policy exceptions
        policy_exceptions = []
        for d in overridden:
            if d.policy_exception_flags:
                policy_exceptions.append({
                    "case_id": str(d.case_id),
                    "flags": d.policy_exception_flags,
                    "reason": d.override_reason,
                    "overridden_at": d.overridden_at.isoformat() if d.overridden_at else None,
                })

        # High risk loans
        high_risk = [
            l for l in loans
            if l.original_risk_band in {RiskBand.HIGH, RiskBand.VERY_HIGH}
        ]
        high_risk_entries = []
        for loan in high_risk[:20]:
            kirana = kirana_map.get(str(loan.kirana_id))
            high_risk_entries.append({
                "loan_id": str(loan.id),
                "kirana_name": kirana.store_name if kirana else "Unknown",
                "principal": loan.principal_amount,
                "outstanding": loan.outstanding_principal or 0,
                "risk_band": loan.original_risk_band.value if loan.original_risk_band else "N/A",
                "status": loan.status.value,
                "dpd": loan.days_past_due,
            })

        logger.info(
            "Compliance report: org=%s, cases=%d, overrides=%d",
            org.name, len(cases), cases_with_overrides,
        )

        return ComplianceReport(
            org_id=str(org_id),
            org_name=org.name,
            total_cases=len(cases),
            total_loans=len(loans),
            cases_with_overrides=cases_with_overrides,
            override_rate_pct=round(override_rate, 1),
            total_audit_events=len(audit_events),
            policy_exceptions=policy_exceptions,
            high_risk_loans=high_risk_entries,
        )

    # ------------------------------------------------------------------
    # JSON Export Helper
    # ------------------------------------------------------------------

    def export_as_json(self, data: BaseModel) -> str:
        """Serialize any export model to formatted JSON."""
        return data.model_dump_json(indent=2)

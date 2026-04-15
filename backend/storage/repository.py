"""
KIRA platform repository.

Provides a simple file-backed persistence layer for Phase 8 entities.
This intentionally mirrors the lightweight persistence approach used by
assessment outputs so the platform foundation can be built without adding
database infrastructure yet.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, TypeAdapter

from models.output_schema import AssessmentOutput, RiskBand, ValueRange
from models.platform_schema import (
    AlertSeverity,
    AlertStatus,
    AssessmentCase,
    AssessmentSummary,
    AuditAction,
    AuditEntityType,
    AuditEvent,
    CaseStatus,
    DashboardSummary,
    DocumentBundle,
    KiranaLocation,
    KiranaProfile,
    LenderOrg,
    LoanAccount,
    MonitoringRun,
    PlatformSnapshot,
    PlatformUser,
    RiskAlert,
    StatementUpload,
    UnderwritingDecision,
    UserRole,
)

logger = logging.getLogger("kira.platform_repository")

T = TypeVar("T", bound=BaseModel)


def _fixed_uuid(value: str) -> uuid.UUID:
    return uuid.UUID(value)


class PlatformRepository:
    """File-backed repository for platform entities and demo data."""

    def __init__(self) -> None:
        self._data_dir = Path(__file__).resolve().parent.parent / "data" / "platform"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._file_map = {
            "organizations": self._data_dir / "organizations.json",
            "users": self._data_dir / "users.json",
            "kiranas": self._data_dir / "kiranas.json",
            "cases": self._data_dir / "cases.json",
            "alerts": self._data_dir / "alerts.json",
            "audit_events": self._data_dir / "audit_events.json",
            "assessment_summaries": self._data_dir / "assessment_summaries.json",
            "document_bundles": self._data_dir / "document_bundles.json",
            "underwriting_decisions": self._data_dir / "underwriting_decisions.json",
            "loan_accounts": self._data_dir / "loan_accounts.json",
            "statement_uploads": self._data_dir / "statement_uploads.json",
            "monitoring_runs": self._data_dir / "monitoring_runs.json",
        }

        self.organizations = self._load_collection("organizations", LenderOrg, "id")
        self.users = self._load_collection("users", PlatformUser, "id")
        self.kiranas = self._load_collection("kiranas", KiranaProfile, "id")
        self.cases = self._load_collection("cases", AssessmentCase, "id")
        self.alerts = self._load_collection("alerts", RiskAlert, "id")
        self.audit_events = self._load_collection("audit_events", AuditEvent, "id")
        self.assessment_summaries = self._load_collection(
            "assessment_summaries",
            AssessmentSummary,
            "session_id",
        )
        self.document_bundles = self._load_collection(
            "document_bundles",
            DocumentBundle,
            "id",
        )
        self.underwriting_decisions = self._load_collection(
            "underwriting_decisions",
            UnderwritingDecision,
            "id",
        )
        self.loan_accounts = self._load_collection(
            "loan_accounts",
            LoanAccount,
            "id",
        )
        self.statement_uploads = self._load_collection(
            "statement_uploads",
            StatementUpload,
            "id",
        )
        self.monitoring_runs = self._load_collection(
            "monitoring_runs",
            MonitoringRun,
            "id",
        )

        self._seed_demo_data_if_empty()

    def _load_collection(
        self,
        name: str,
        model_cls: type[T],
        key_field: str,
    ) -> dict[str, T]:
        path = self._file_map[name]
        if not path.exists():
            return {}

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            parsed = TypeAdapter(list[model_cls]).validate_python(raw)
        except Exception as exc:
            logger.warning("Failed to load %s from %s: %s", name, path.name, exc)
            return {}

        result: dict[str, T] = {}
        for item in parsed:
            result[str(getattr(item, key_field))] = item
        return result

    def _save_collection(self, name: str, collection: dict[str, BaseModel]) -> None:
        path = self._file_map[name]
        payload = [
            model.model_dump(mode="json")
            for model in sorted(
                collection.values(),
                key=lambda item: getattr(item, "created_at", datetime.min),
            )
        ]
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _save_all(self) -> None:
        self._save_collection("organizations", self.organizations)
        self._save_collection("users", self.users)
        self._save_collection("kiranas", self.kiranas)
        self._save_collection("cases", self.cases)
        self._save_collection("alerts", self.alerts)
        self._save_collection("audit_events", self.audit_events)
        self._save_collection("assessment_summaries", self.assessment_summaries)
        self._save_collection("document_bundles", self.document_bundles)
        self._save_collection("underwriting_decisions", self.underwriting_decisions)
        self._save_collection("loan_accounts", self.loan_accounts)
        self._save_collection("statement_uploads", self.statement_uploads)
        self._save_collection("monitoring_runs", self.monitoring_runs)

    def _seed_demo_data_if_empty(self) -> None:
        if self.organizations:
            return

        now = datetime.utcnow()
        org = LenderOrg(
            id=_fixed_uuid("11111111-1111-1111-1111-111111111111"),
            name="Demo Capital Finance",
            slug="demo-capital-finance",
            created_at=now - timedelta(days=30),
            is_demo=True,
        )
        admin = PlatformUser(
            id=_fixed_uuid("21111111-1111-1111-1111-111111111111"),
            org_id=org.id,
            full_name="Maya Sharma",
            email="maya@democapital.in",
            role=UserRole.ADMIN,
            created_at=now - timedelta(days=29),
        )
        officer = PlatformUser(
            id=_fixed_uuid("22222222-2222-2222-2222-222222222222"),
            org_id=org.id,
            full_name="Rohan Verma",
            email="rohan@democapital.in",
            role=UserRole.LOAN_OFFICER,
            created_at=now - timedelta(days=28),
        )

        kirana_1 = KiranaProfile(
            id=_fixed_uuid("31111111-1111-1111-1111-111111111111"),
            org_id=org.id,
            store_name="Gupta General Store",
            owner_name="Sanjay Gupta",
            owner_mobile="+91-9876543210",
            location=KiranaLocation(
                state="Uttar Pradesh",
                district="Meerut",
                pin_code="250002",
                locality="Shastri Nagar",
            ),
            metadata={"shop_size": "medium"},
            created_at=now - timedelta(days=12),
            updated_at=now - timedelta(days=4),
        )
        kirana_2 = KiranaProfile(
            id=_fixed_uuid("32222222-2222-2222-2222-222222222222"),
            org_id=org.id,
            store_name="Sai Provision Mart",
            owner_name="Vijay Patil",
            owner_mobile="+91-9123456780",
            location=KiranaLocation(
                state="Maharashtra",
                district="Pune",
                pin_code="411014",
                locality="Viman Nagar",
            ),
            metadata={"shop_size": "small"},
            created_at=now - timedelta(days=10),
            updated_at=now - timedelta(days=2),
        )
        kirana_3 = KiranaProfile(
            id=_fixed_uuid("33333333-3333-3333-3333-333333333333"),
            org_id=org.id,
            store_name="A One Kirana",
            owner_name="Imran Khan",
            owner_mobile="+91-9988776655",
            location=KiranaLocation(
                state="Delhi",
                district="North East Delhi",
                pin_code="110094",
                locality="Karawal Nagar",
            ),
            metadata={"shop_size": "large"},
            created_at=now - timedelta(days=8),
            updated_at=now - timedelta(days=1),
        )

        summary_1 = AssessmentSummary(
            session_id=_fixed_uuid("41111111-1111-1111-1111-111111111111"),
            assessment_id=_fixed_uuid("51111111-1111-1111-1111-111111111111"),
            completed_at=now - timedelta(days=4),
            risk_band=RiskBand.MEDIUM,
            risk_score=0.41,
            revenue_range=ValueRange(low=180000, high=320000),
            loan_range=ValueRange(low=90000, high=180000),
            eligible=True,
            fraud_flagged=False,
        )
        summary_2 = AssessmentSummary(
            session_id=_fixed_uuid("42222222-2222-2222-2222-222222222222"),
            assessment_id=_fixed_uuid("52222222-2222-2222-2222-222222222222"),
            completed_at=now - timedelta(days=2),
            risk_band=RiskBand.LOW,
            risk_score=0.28,
            revenue_range=ValueRange(low=210000, high=360000),
            loan_range=ValueRange(low=120000, high=220000),
            eligible=True,
            fraud_flagged=False,
        )
        summary_3 = AssessmentSummary(
            session_id=_fixed_uuid("43333333-3333-3333-3333-333333333333"),
            assessment_id=_fixed_uuid("53333333-3333-3333-3333-333333333333"),
            completed_at=now - timedelta(days=1),
            risk_band=RiskBand.HIGH,
            risk_score=0.67,
            revenue_range=ValueRange(low=90000, high=150000),
            loan_range=ValueRange(low=40000, high=80000),
            eligible=True,
            fraud_flagged=True,
        )

        case_1 = AssessmentCase(
            id=_fixed_uuid("61111111-1111-1111-1111-111111111111"),
            org_id=org.id,
            kirana_id=kirana_1.id,
            created_by_user_id=admin.id,
            assigned_to_user_id=officer.id,
            status=CaseStatus.UNDER_REVIEW,
            latest_assessment_session_id=summary_1.session_id,
            latest_assessment_id=summary_1.assessment_id,
            latest_risk_band=summary_1.risk_band,
            latest_loan_range=summary_1.loan_range,
            notes="Waiting for lender override decision.",
            created_at=now - timedelta(days=4),
            updated_at=now - timedelta(days=4),
        )
        case_2 = AssessmentCase(
            id=_fixed_uuid("62222222-2222-2222-2222-222222222222"),
            org_id=org.id,
            kirana_id=kirana_2.id,
            created_by_user_id=admin.id,
            assigned_to_user_id=officer.id,
            status=CaseStatus.MONITORING,
            latest_assessment_session_id=summary_2.session_id,
            latest_assessment_id=summary_2.assessment_id,
            latest_risk_band=summary_2.risk_band,
            latest_loan_range=summary_2.loan_range,
            notes="Disbursed last week, monitoring first refresh cycle.",
            created_at=now - timedelta(days=6),
            updated_at=now - timedelta(days=2),
        )
        case_3 = AssessmentCase(
            id=_fixed_uuid("63333333-3333-3333-3333-333333333333"),
            org_id=org.id,
            kirana_id=kirana_3.id,
            created_by_user_id=officer.id,
            assigned_to_user_id=officer.id,
            status=CaseStatus.SUBMITTED,
            latest_assessment_session_id=summary_3.session_id,
            latest_assessment_id=summary_3.assessment_id,
            latest_risk_band=summary_3.risk_band,
            latest_loan_range=summary_3.loan_range,
            notes="Requires deeper review because of fraud signal mismatch.",
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(days=1),
        )

        alert = RiskAlert(
            id=_fixed_uuid("71111111-1111-1111-1111-111111111111"),
            org_id=org.id,
            case_id=case_2.id,
            kirana_id=kirana_2.id,
            severity=AlertSeverity.WARNING,
            status=AlertStatus.OPEN,
            title="Fresh statement upload pending",
            description="Monitoring case has crossed the 15-day refresh mark.",
            created_at=now - timedelta(hours=18),
            updated_at=now - timedelta(hours=18),
        )

        seed_event = AuditEvent(
            id=_fixed_uuid("81111111-1111-1111-1111-111111111111"),
            org_id=org.id,
            entity_type=AuditEntityType.SYSTEM,
            entity_id=org.id,
            action=AuditAction.SEEDED,
            description="Seeded default Phase 8 demo workspace.",
            actor_name="system",
            metadata={"demo_org_slug": org.slug},
            created_at=now - timedelta(days=30),
        )

        self.organizations[str(org.id)] = org
        self.users[str(admin.id)] = admin
        self.users[str(officer.id)] = officer
        self.kiranas[str(kirana_1.id)] = kirana_1
        self.kiranas[str(kirana_2.id)] = kirana_2
        self.kiranas[str(kirana_3.id)] = kirana_3
        self.assessment_summaries[str(summary_1.session_id)] = summary_1
        self.assessment_summaries[str(summary_2.session_id)] = summary_2
        self.assessment_summaries[str(summary_3.session_id)] = summary_3
        self.cases[str(case_1.id)] = case_1
        self.cases[str(case_2.id)] = case_2
        self.cases[str(case_3.id)] = case_3
        self.alerts[str(alert.id)] = alert
        self.audit_events[str(seed_event.id)] = seed_event

        self._save_all()
        logger.info("Seeded Phase 8 demo platform data")

    def list_organizations(self) -> list[LenderOrg]:
        return sorted(self.organizations.values(), key=lambda item: item.created_at)

    def get_organization(self, org_id: uuid.UUID) -> LenderOrg | None:
        return self.organizations.get(str(org_id))

    def list_users(self, org_id: uuid.UUID | None = None) -> list[PlatformUser]:
        users = list(self.users.values())
        if org_id is not None:
            users = [user for user in users if user.org_id == org_id]
        return sorted(users, key=lambda item: item.created_at)

    def get_user(self, user_id: uuid.UUID) -> PlatformUser | None:
        return self.users.get(str(user_id))

    def list_kiranas(self, org_id: uuid.UUID | None = None) -> list[KiranaProfile]:
        kiranas = list(self.kiranas.values())
        if org_id is not None:
            kiranas = [kirana for kirana in kiranas if kirana.org_id == org_id]
        return sorted(kiranas, key=lambda item: item.updated_at, reverse=True)

    def get_kirana(self, kirana_id: uuid.UUID) -> KiranaProfile | None:
        return self.kiranas.get(str(kirana_id))

    def create_kirana(self, kirana: KiranaProfile) -> KiranaProfile:
        self.kiranas[str(kirana.id)] = kirana
        self._save_collection("kiranas", self.kiranas)
        return kirana

    def update_kirana(self, kirana: KiranaProfile) -> KiranaProfile:
        """Update an existing kirana profile."""
        self.kiranas[str(kirana.id)] = kirana
        self._save_collection("kiranas", self.kiranas)
        return kirana

    def find_kirana(
        self,
        org_id: uuid.UUID,
        store_name: str,
        pin_code: str,
    ) -> KiranaProfile | None:
        """Find a kirana by store name (case-insensitive) and PIN code within an org."""
        name_lower = store_name.strip().lower()
        pin_clean = pin_code.strip()
        for kirana in self.kiranas.values():
            if (
                kirana.org_id == org_id
                and kirana.store_name.strip().lower() == name_lower
                and kirana.location.pin_code.strip() == pin_clean
            ):
                return kirana
        return None

    def list_cases(self, org_id: uuid.UUID | None = None) -> list[AssessmentCase]:
        cases = list(self.cases.values())
        if org_id is not None:
            cases = [case for case in cases if case.org_id == org_id]
        return sorted(cases, key=lambda item: item.updated_at, reverse=True)

    def get_case(self, case_id: uuid.UUID) -> AssessmentCase | None:
        return self.cases.get(str(case_id))

    def create_case(self, case: AssessmentCase) -> AssessmentCase:
        self.cases[str(case.id)] = case
        self._save_collection("cases", self.cases)
        return case

    def update_case(self, case: AssessmentCase) -> AssessmentCase:
        self.cases[str(case.id)] = case
        self._save_collection("cases", self.cases)
        return case

    def list_alerts(
        self,
        org_id: uuid.UUID | None = None,
        status: AlertStatus | None = None,
        case_id: uuid.UUID | None = None,
        kirana_id: uuid.UUID | None = None,
    ) -> list[RiskAlert]:
        alerts = list(self.alerts.values())
        if org_id is not None:
            alerts = [alert for alert in alerts if alert.org_id == org_id]
        if status is not None:
            alerts = [alert for alert in alerts if alert.status == status]
        if case_id is not None:
            alerts = [alert for alert in alerts if alert.case_id == case_id]
        if kirana_id is not None:
            alerts = [alert for alert in alerts if alert.kirana_id == kirana_id]
        return sorted(alerts, key=lambda item: item.created_at, reverse=True)

    def create_alert(self, alert: RiskAlert) -> RiskAlert:
        """Create a new risk alert."""
        self.alerts[str(alert.id)] = alert
        self._save_collection("alerts", self.alerts)
        return alert

    def list_document_bundles(
        self,
        org_id: uuid.UUID | None = None,
        case_id: uuid.UUID | None = None,
    ) -> list[DocumentBundle]:
        bundles = list(self.document_bundles.values())
        if org_id is not None:
            bundles = [bundle for bundle in bundles if bundle.org_id == org_id]
        if case_id is not None:
            bundles = [bundle for bundle in bundles if bundle.case_id == case_id]
        return sorted(bundles, key=lambda item: item.created_at, reverse=True)

    def create_audit_event(self, event: AuditEvent) -> AuditEvent:
        self.audit_events[str(event.id)] = event
        self._save_collection("audit_events", self.audit_events)
        return event

    def save_underwriting_decision(
        self,
        decision: UnderwritingDecision,
    ) -> UnderwritingDecision:
        self.underwriting_decisions[str(decision.id)] = decision
        self._save_collection("underwriting_decisions", self.underwriting_decisions)
        return decision

    def list_underwriting_decisions(
        self,
        case_id: uuid.UUID | None = None,
        assessment_session_id: uuid.UUID | None = None,
    ) -> list[UnderwritingDecision]:
        decisions = list(self.underwriting_decisions.values())
        if case_id is not None:
            decisions = [item for item in decisions if item.case_id == case_id]
        if assessment_session_id is not None:
            decisions = [
                item for item in decisions
                if item.assessment_session_id == assessment_session_id
            ]
        return sorted(decisions, key=lambda item: item.updated_at, reverse=True)

    def get_latest_underwriting_decision(
        self,
        case_id: uuid.UUID,
        assessment_session_id: uuid.UUID | None = None,
    ) -> UnderwritingDecision | None:
        decisions = self.list_underwriting_decisions(
            case_id=case_id,
            assessment_session_id=assessment_session_id,
        )
        return decisions[0] if decisions else None

    def list_audit_events(
        self,
        org_id: uuid.UUID | None = None,
        entity_id: uuid.UUID | None = None,
    ) -> list[AuditEvent]:
        events = list(self.audit_events.values())
        if org_id is not None:
            events = [event for event in events if event.org_id == org_id]
        if entity_id is not None:
            events = [event for event in events if event.entity_id == entity_id]
        return sorted(events, key=lambda item: item.created_at, reverse=True)

    # ------------------------------------------------------------------
    # Phase 11 — Loan Accounts
    # ------------------------------------------------------------------

    def create_loan_account(self, loan: LoanAccount) -> LoanAccount:
        self.loan_accounts[str(loan.id)] = loan
        self._save_collection("loan_accounts", self.loan_accounts)
        return loan

    def update_loan_account(self, loan: LoanAccount) -> LoanAccount:
        self.loan_accounts[str(loan.id)] = loan
        self._save_collection("loan_accounts", self.loan_accounts)
        return loan

    def get_loan_account(self, loan_id: uuid.UUID) -> LoanAccount | None:
        return self.loan_accounts.get(str(loan_id))

    def list_loan_accounts(
        self,
        org_id: uuid.UUID | None = None,
        case_id: uuid.UUID | None = None,
        kirana_id: uuid.UUID | None = None,
    ) -> list[LoanAccount]:
        loans = list(self.loan_accounts.values())
        if org_id is not None:
            loans = [l for l in loans if l.org_id == org_id]
        if case_id is not None:
            loans = [l for l in loans if l.case_id == case_id]
        if kirana_id is not None:
            loans = [l for l in loans if l.kirana_id == kirana_id]
        return sorted(loans, key=lambda item: item.created_at, reverse=True)

    # ------------------------------------------------------------------
    # Phase 11 — Statement Uploads
    # ------------------------------------------------------------------

    def create_statement_upload(self, upload: StatementUpload) -> StatementUpload:
        self.statement_uploads[str(upload.id)] = upload
        self._save_collection("statement_uploads", self.statement_uploads)
        return upload

    def update_statement_upload(self, upload: StatementUpload) -> StatementUpload:
        self.statement_uploads[str(upload.id)] = upload
        self._save_collection("statement_uploads", self.statement_uploads)
        return upload

    def list_statement_uploads(
        self,
        loan_id: uuid.UUID | None = None,
        case_id: uuid.UUID | None = None,
    ) -> list[StatementUpload]:
        uploads = list(self.statement_uploads.values())
        if loan_id is not None:
            uploads = [u for u in uploads if u.loan_id == loan_id]
        if case_id is not None:
            uploads = [u for u in uploads if u.case_id == case_id]
        return sorted(uploads, key=lambda item: item.created_at, reverse=True)

    # ------------------------------------------------------------------
    # Phase 11 — Monitoring Runs
    # ------------------------------------------------------------------

    def create_monitoring_run(self, run: MonitoringRun) -> MonitoringRun:
        self.monitoring_runs[str(run.id)] = run
        self._save_collection("monitoring_runs", self.monitoring_runs)
        return run

    def list_monitoring_runs(
        self,
        loan_id: uuid.UUID | None = None,
        case_id: uuid.UUID | None = None,
    ) -> list[MonitoringRun]:
        runs = list(self.monitoring_runs.values())
        if loan_id is not None:
            runs = [r for r in runs if r.loan_id == loan_id]
        if case_id is not None:
            runs = [r for r in runs if r.case_id == case_id]
        return sorted(runs, key=lambda item: item.created_at, reverse=True)

    def upsert_assessment_summary(self, output: AssessmentOutput) -> AssessmentSummary:
        summary = AssessmentSummary(
            session_id=output.session_id,
            assessment_id=output.assessment_id,
            completed_at=output.timestamp,
            status=output.status,
            risk_band=output.risk_assessment.risk_band,
            risk_score=output.risk_assessment.risk_score,
            revenue_range=ValueRange(
                low=output.revenue_estimate.monthly_low,
                high=output.revenue_estimate.monthly_high,
            ),
            loan_range=output.loan_recommendation.loan_range,
            recommended_amount=output.loan_recommendation.recommended_amount,
            suggested_tenure_months=output.loan_recommendation.suggested_tenure_months,
            estimated_emi=output.loan_recommendation.estimated_emi,
            emi_to_income_ratio=output.loan_recommendation.emi_to_income_ratio,
            repayment_cadence=output.loan_recommendation.repayment_cadence,
            estimated_installment=output.loan_recommendation.estimated_installment,
            pricing_recommendation=output.loan_recommendation.pricing_recommendation,
            explanation_summary=output.explanation.summary,
            decision_pack=output.explanation.decision_pack,
            eligible=output.loan_recommendation.eligible,
            fraud_flagged=output.fraud_detection.is_flagged,
        )
        self.assessment_summaries[str(summary.session_id)] = summary
        self._save_collection("assessment_summaries", self.assessment_summaries)
        return summary

    def get_assessment_summary(self, session_id: uuid.UUID) -> AssessmentSummary | None:
        return self.assessment_summaries.get(str(session_id))

    def build_dashboard_summary(self, org_id: uuid.UUID) -> DashboardSummary:
        cases = self.list_cases(org_id)
        kiranas = self.list_kiranas(org_id)
        alerts = self.list_alerts(org_id=org_id, status=AlertStatus.OPEN)

        cases_by_status = {status.value: 0 for status in CaseStatus}
        linked_assessments = 0
        flagged_assessments = 0

        for case in cases:
            cases_by_status[case.status.value] = cases_by_status.get(case.status.value, 0) + 1
            if case.latest_assessment_session_id:
                linked_assessments += 1
                summary = self.get_assessment_summary(case.latest_assessment_session_id)
                if summary and summary.fraud_flagged:
                    flagged_assessments += 1

        return DashboardSummary(
            total_kiranas=len(kiranas),
            total_cases=len(cases),
            linked_assessments=linked_assessments,
            open_alerts=len(alerts),
            flagged_assessments=flagged_assessments,
            cases_by_status=cases_by_status,
        )

    def get_platform_snapshot(self) -> PlatformSnapshot:
        return PlatformSnapshot(
            organizations=self.list_organizations(),
            users=self.list_users(),
            kiranas=self.list_kiranas(),
            cases=self.list_cases(),
            alerts=self.list_alerts(),
            audit_events=self.list_audit_events(),
            assessment_summaries=sorted(
                self.assessment_summaries.values(),
                key=lambda item: item.completed_at,
                reverse=True,
            ),
            document_bundles=self.list_document_bundles(),
            underwriting_decisions=self.list_underwriting_decisions(),
            loan_accounts=self.list_loan_accounts(),
            statement_uploads=self.list_statement_uploads(),
            monitoring_runs=self.list_monitoring_runs(),
        )


_platform_repository: PlatformRepository | None = None


def get_platform_repository() -> PlatformRepository:
    global _platform_repository
    if _platform_repository is None:
        _platform_repository = PlatformRepository()
    return _platform_repository

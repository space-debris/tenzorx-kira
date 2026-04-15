"""
Phase 12 + 13 integration tests.

Phase 12: Portfolio metrics and cohort analysis.
Phase 13: Document builder and compliance exporter.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest

from models.output_schema import RepaymentCadence, RiskBand
from models.platform_schema import (
    AssessmentCase,
    AssessmentSummary,
    CaseStatus,
    KiranaLocation,
    KiranaProfile,
    LoanAccount,
    LoanAccountStatus,
    UnderwritingDecision,
    UnderwritingTerms,
)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


def _make_kirana(org_id: uuid.UUID, state: str = "Maharashtra") -> KiranaProfile:
    return KiranaProfile(
        org_id=org_id,
        store_name=f"Test Store {uuid.uuid4().hex[:4]}",
        owner_name="Test Owner",
        owner_mobile="9876543210",
        location=KiranaLocation(
            latitude=19.0,
            longitude=72.8,
            address="Test Address",
            locality="Test Area",
            district="Mumbai",
            state=state,
            pin_code="400001",
        ),
    )


def _make_case(org_id: uuid.UUID, kirana_id: uuid.UUID) -> AssessmentCase:
    return AssessmentCase(
        org_id=org_id,
        kirana_id=kirana_id,
        status=CaseStatus.APPROVED,
        created_by_user_id=uuid.uuid4(),
    )


def _make_loan(
    org_id: uuid.UUID,
    case_id: uuid.UUID,
    kirana_id: uuid.UUID,
    status: LoanAccountStatus = LoanAccountStatus.ACTIVE,
    risk_band: RiskBand = RiskBand.MEDIUM,
    principal: float = 150000,
    dpd: int = 0,
) -> LoanAccount:
    return LoanAccount(
        org_id=org_id,
        case_id=case_id,
        kirana_id=kirana_id,
        assessment_session_id=uuid.uuid4(),
        status=status,
        principal_amount=principal,
        outstanding_principal=principal * 0.8,
        tenure_months=12,
        repayment_cadence=RepaymentCadence.WEEKLY,
        annual_interest_rate_pct=18.0,
        processing_fee_pct=1.5,
        estimated_installment=3500,
        original_risk_band=risk_band,
        days_past_due=dpd,
        disbursed_at=datetime.utcnow() - timedelta(days=60),
    )


# ---------------------------------------------------------------------------
# Phase 12 Tests — Portfolio Metrics
# ---------------------------------------------------------------------------


class TestPortfolioMetrics:
    """Tests for analytics.portfolio_metrics."""

    def test_portfolio_kpis_model(self):
        from analytics.portfolio_metrics import PortfolioKpis

        kpis = PortfolioKpis(
            total_kiranas=10,
            total_cases=15,
            total_loans=8,
            active_loans=5,
            total_disbursed=1200000,
            total_outstanding=800000,
        )
        assert kpis.total_kiranas == 10
        assert kpis.total_outstanding == 800000

    def test_portfolio_summary_model(self):
        from analytics.portfolio_metrics import (
            GeographicConcentration,
            PortfolioKpis,
            PortfolioSummary,
            RiskDistribution,
            StatusBreakdown,
        )

        summary = PortfolioSummary(
            kpis=PortfolioKpis(),
            risk_distribution=RiskDistribution(low=3, medium=4, high=2, very_high=1),
            geographic_concentration=GeographicConcentration(by_state={"MH": 5}),
            status_breakdown=StatusBreakdown(cases_by_status={"approved": 3}),
        )
        assert summary.risk_distribution.low == 3
        assert summary.geographic_concentration.by_state["MH"] == 5


class TestCohortAnalysis:
    """Tests for analytics.cohort_analysis."""

    def test_cohort_bucket_creation(self):
        from analytics.cohort_analysis import _build_bucket

        org_id = uuid.uuid4()
        kirana_id = uuid.uuid4()
        case_id = uuid.uuid4()

        loans = [
            _make_loan(org_id, case_id, kirana_id, principal=100000, dpd=0),
            _make_loan(org_id, case_id, kirana_id, principal=200000, dpd=10),
            _make_loan(
                org_id, case_id, kirana_id,
                principal=150000, dpd=40,
                status=LoanAccountStatus.OVERDUE,
            ),
        ]

        bucket = _build_bucket("test-cohort", loans)
        assert bucket.label == "test-cohort"
        assert bucket.loan_count == 3
        assert bucket.total_disbursed == 450000
        assert bucket.overdue_pct > 0

    def test_empty_cohort(self):
        from analytics.cohort_analysis import _build_bucket

        bucket = _build_bucket("empty", [])
        assert bucket.loan_count == 0
        assert bucket.total_disbursed == 0

    def test_cohort_analysis_result_model(self):
        from analytics.cohort_analysis import CohortAnalysisResult, CohortSeries

        result = CohortAnalysisResult(
            by_vintage=CohortSeries(dimension="vintage"),
            by_risk_tier=CohortSeries(dimension="risk"),
            by_state=CohortSeries(dimension="state"),
            by_cadence=CohortSeries(dimension="cadence"),
        )
        assert result.by_vintage.dimension == "vintage"


# ---------------------------------------------------------------------------
# Phase 13 Tests — Document Builder
# ---------------------------------------------------------------------------


class TestDocumentBuilder:
    """Tests for services.document_builder."""

    def test_underwriting_summary_generation(self):
        from services.document_builder import build_underwriting_summary

        org_id = uuid.uuid4()
        kirana = _make_kirana(org_id)
        case = _make_case(org_id, kirana.id)

        doc = build_underwriting_summary(case, kirana, None, None)

        assert doc.document_type == "underwriting_summary"
        assert kirana.store_name in doc.title
        assert len(doc.sections) >= 1
        assert doc.sections[0].title == "Borrower Profile"
        assert kirana.store_name in doc.sections[0].content

    def test_underwriting_summary_with_assessment(self):
        from models.output_schema import ValueRange
        from services.document_builder import build_underwriting_summary

        org_id = uuid.uuid4()
        kirana = _make_kirana(org_id)
        case = _make_case(org_id, kirana.id)

        assessment = AssessmentSummary(
            session_id=uuid.uuid4(),
            assessment_id=uuid.uuid4(),
            completed_at=datetime.utcnow(),
            status="completed",
            risk_band=RiskBand.LOW,
            risk_score=0.25,
            revenue_range=ValueRange(low=80000, high=120000),
            loan_range=ValueRange(low=100000, high=200000),
            recommended_amount=150000,
            suggested_tenure_months=12,
            eligible=True,
            fraud_flagged=False,
        )

        doc = build_underwriting_summary(case, kirana, assessment, None)

        assert len(doc.sections) >= 3
        section_titles = [s.title for s in doc.sections]
        assert "Assessment Results" in section_titles
        assert "Loan Recommendation" in section_titles

    def test_sanction_note_generation(self):
        from services.document_builder import build_sanction_note

        org_id = uuid.uuid4()
        kirana = _make_kirana(org_id)
        case = _make_case(org_id, kirana.id)

        from models.output_schema import ValueRange

        decision = UnderwritingDecision(
            org_id=org_id,
            case_id=case.id,
            kirana_id=kirana.id,
            assessment_session_id=uuid.uuid4(),
            assessment_id=uuid.uuid4(),
            loan_range_guardrail=ValueRange(low=100000, high=200000),
            eligible=True,
            has_override=False,
            final_terms=UnderwritingTerms(
                amount=150000,
                tenure_months=12,
                repayment_cadence=RepaymentCadence.WEEKLY,
                annual_interest_rate_pct=18.0,
                processing_fee_pct=1.5,
                estimated_installment=3500,
            ),
        )

        doc = build_sanction_note(case, kirana, decision)

        assert doc.document_type == "sanction_note"
        assert len(doc.sections) >= 2
        assert "150,000" in doc.sections[1].content

    def test_monitoring_summary_generation(self):
        from services.document_builder import build_monitoring_summary

        org_id = uuid.uuid4()
        kirana = _make_kirana(org_id)
        loan = _make_loan(org_id, uuid.uuid4(), kirana.id)

        doc = build_monitoring_summary(loan, kirana, None)

        assert doc.document_type == "monitoring_summary"
        assert "Loan Overview" in [s.title for s in doc.sections]


# ---------------------------------------------------------------------------
# Phase 13 Tests — Compliance Exporter
# ---------------------------------------------------------------------------


class TestComplianceExporter:
    """Tests for services.compliance_exporter."""

    def test_audit_export_bundle_model(self):
        from services.compliance_exporter import AuditExportBundle

        bundle = AuditExportBundle(
            org_id="test-org",
            total_events=5,
            events=[],
        )
        assert bundle.org_id == "test-org"
        assert bundle.total_events == 5

    def test_case_file_packet_model(self):
        from services.compliance_exporter import CaseFilePacket

        packet = CaseFilePacket(
            case_id="test-case",
            kirana_name="Test Store",
        )
        assert packet.case_id == "test-case"
        assert len(packet.documents) == 0

    def test_compliance_report_model(self):
        from services.compliance_exporter import ComplianceReport

        report = ComplianceReport(
            org_id="test-org",
            org_name="Test Org",
            total_cases=10,
            total_loans=5,
            cases_with_overrides=2,
            override_rate_pct=20.0,
        )
        assert report.override_rate_pct == 20.0
        assert report.total_cases == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Phase 11 integration tests — Loan Lifecycle & Monitoring.

Tests the end-to-end flow:
  1. Loan booking from an approved case
  2. Statement upload and parsing
  3. Monitoring re-assessment cycle
  4. Utilization classification
  5. Restructuring advisor logic
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timedelta

import pytest

# ---------------------------------------------------------------------------
# Test utilities
# ---------------------------------------------------------------------------


def _build_csv_statement(
    credits: list[float] | None = None,
    debits: list[float] | None = None,
    days: int = 30,
) -> bytes:
    """Generate a synthetic CSV bank statement."""
    if credits is None:
        credits = [15000, 22000, 18000, 9500, 31000, 12000]
    if debits is None:
        debits = [8000, 5500, 12000, 3000, 7000, 9000, 4500]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Description", "Debit", "Credit", "Balance"])

    base_date = datetime.utcnow() - timedelta(days=days)
    balance = 50000.0
    rows = max(len(credits), len(debits))

    for i in range(rows):
        date_str = (base_date + timedelta(days=i)).strftime("%d/%m/%Y")
        if i < len(credits):
            balance += credits[i]
            writer.writerow([date_str, f"UPI Credit {i+1}", "", f"{credits[i]:.2f}", f"{balance:.2f}"])
        if i < len(debits):
            balance -= debits[i]
            writer.writerow([date_str, f"Debit Txn {i+1}", f"{debits[i]:.2f}", "", f"{balance:.2f}"])

    return output.getvalue().encode("utf-8")


# ---------------------------------------------------------------------------
# 1. Statement Parser Tests
# ---------------------------------------------------------------------------


class TestStatementParser:
    """Tests for the statement_parser module."""

    def test_csv_parsing_produces_valid_summary(self):
        from models.platform_schema import StatementUpload, StatementUploadStatus
        from services.statement_parser import parse_statement

        upload = StatementUpload(
            org_id=uuid.uuid4(),
            case_id=uuid.uuid4(),
            loan_id=uuid.uuid4(),
            kirana_id=uuid.uuid4(),
            file_name="test_statement.csv",
            file_type="csv",
            file_size_bytes=1024,
        )

        csv_content = _build_csv_statement(
            credits=[10000, 20000, 30000],
            debits=[5000, 15000],
        )

        result = parse_statement(upload, csv_content)

        assert result.status == StatementUploadStatus.PARSED
        assert result.transaction_summary is not None
        assert result.transaction_summary.total_credits == 60000.0
        assert result.transaction_summary.total_debits == 20000.0
        assert result.transaction_summary.credit_count == 3
        assert result.transaction_summary.debit_count == 2
        assert result.parse_error is None

    def test_invalid_file_type_returns_failed(self):
        from models.platform_schema import StatementUpload, StatementUploadStatus
        from services.statement_parser import parse_statement

        upload = StatementUpload(
            org_id=uuid.uuid4(),
            case_id=uuid.uuid4(),
            loan_id=uuid.uuid4(),
            kirana_id=uuid.uuid4(),
            file_name="test.xlsx",
            file_type="xlsx",
            file_size_bytes=512,
        )

        result = parse_statement(upload, b"some binary content")
        assert result.status == StatementUploadStatus.FAILED
        assert result.parse_error is not None
        assert "Unsupported" in result.parse_error

    def test_pdf_heuristic_produces_summary(self):
        from models.platform_schema import StatementUpload, StatementUploadStatus
        from services.statement_parser import parse_statement

        upload = StatementUpload(
            org_id=uuid.uuid4(),
            case_id=uuid.uuid4(),
            loan_id=uuid.uuid4(),
            kirana_id=uuid.uuid4(),
            file_name="bank_statement.pdf",
            file_type="pdf",
            file_size_bytes=50000,
        )

        # Simulate a minimal PDF-ish content
        result = parse_statement(upload, b"%PDF-1.4 dummy content " * 100)
        assert result.status == StatementUploadStatus.PARSED
        assert result.transaction_summary is not None
        assert result.transaction_summary.total_credits > 0


# ---------------------------------------------------------------------------
# 2. Utilization Tracker Tests
# ---------------------------------------------------------------------------


class TestUtilizationTracker:
    """Tests for the utilization_tracker module."""

    def test_aggregate_classification_produces_valid_breakdown(self):
        from models.platform_schema import TransactionSummary
        from orchestration.utilization_tracker import classify_utilization

        summary = TransactionSummary(
            total_credits=250000,
            total_debits=180000,
            credit_count=35,
            debit_count=50,
            avg_daily_balance=25000,
            period_days=30,
        )

        result = classify_utilization(summary)

        total_pct = (
            result.supplier_inventory_pct
            + result.transfer_wallet_pct
            + result.personal_cash_pct
            + result.unknown_pct
        )
        assert 99.0 <= total_pct <= 101.0, f"Percentages don't sum to ~100: {total_pct}"
        assert result.diversion_risk in ("low", "medium", "high", "unknown")

    def test_none_summary_returns_unknown(self):
        from orchestration.utilization_tracker import classify_utilization

        result = classify_utilization(None)
        assert result.unknown_pct == 100
        assert result.diversion_risk == "unknown"

    def test_keyword_classification(self):
        from models.platform_schema import TransactionSummary
        from orchestration.utilization_tracker import classify_utilization

        summary = TransactionSummary(
            total_credits=100000,
            total_debits=80000,
            credit_count=10,
            debit_count=10,
            avg_daily_balance=15000,
            period_days=30,
        )

        descriptions = [
            "Wholesale supplier payment",
            "ATM cash withdrawal",
            "UPI to PhonePe",
            "Distributor FMCG order",
            "Personal rent payment",
            "Unknown transaction",
            "Stock purchase from wholesaler",
            "PhonePe transfer",
            "NEFT to savings",
            "Grocery wholesale",
        ]

        result = classify_utilization(summary, debit_descriptions=descriptions)
        assert result.supplier_inventory_pct > 0
        assert result.transfer_wallet_pct > 0


# ---------------------------------------------------------------------------
# 3. Restructuring Advisor Tests
# ---------------------------------------------------------------------------


class TestRestructuringAdvisor:
    """Tests for the restructuring_advisor module."""

    def test_no_restructuring_for_healthy_loan(self):
        from models.output_schema import RepaymentCadence, RiskBand
        from models.platform_schema import LoanAccount, TransactionSummary
        from orchestration.restructuring_advisor import assess_restructuring_need

        loan = LoanAccount(
            org_id=uuid.uuid4(),
            case_id=uuid.uuid4(),
            kirana_id=uuid.uuid4(),
            assessment_session_id=uuid.uuid4(),
            principal_amount=150000,
            tenure_months=18,
            repayment_cadence=RepaymentCadence.WEEKLY,
            annual_interest_rate_pct=18.0,
            processing_fee_pct=1.5,
            estimated_installment=2500,
            days_past_due=0,
            original_risk_band=RiskBand.LOW,
        )

        current = TransactionSummary(
            total_credits=250000, total_debits=180000,
            credit_count=40, debit_count=50,
            avg_daily_balance=30000, period_days=30,
        )
        previous = TransactionSummary(
            total_credits=240000, total_debits=170000,
            credit_count=38, debit_count=48,
            avg_daily_balance=28000, period_days=30,
        )

        result = assess_restructuring_need(loan, current, previous, None)
        assert result is None

    def test_suggests_restructuring_for_stressed_loan(self):
        from models.output_schema import RepaymentCadence, RiskBand
        from models.platform_schema import LoanAccount, TransactionSummary
        from orchestration.restructuring_advisor import assess_restructuring_need

        loan = LoanAccount(
            org_id=uuid.uuid4(),
            case_id=uuid.uuid4(),
            kirana_id=uuid.uuid4(),
            assessment_session_id=uuid.uuid4(),
            principal_amount=200000,
            tenure_months=18,
            repayment_cadence=RepaymentCadence.WEEKLY,
            annual_interest_rate_pct=20.0,
            processing_fee_pct=2.0,
            estimated_installment=3500,
            days_past_due=35,
            original_risk_band=RiskBand.MEDIUM,
        )

        current = TransactionSummary(
            total_credits=80000, total_debits=120000,
            credit_count=12, debit_count=25,
            avg_daily_balance=3000, period_days=30,
        )
        previous = TransactionSummary(
            total_credits=200000, total_debits=160000,
            credit_count=30, debit_count=40,
            avg_daily_balance=20000, period_days=30,
        )

        result = assess_restructuring_need(loan, current, previous, None)
        assert result is not None
        assert result.suggestion_type in (
            "emi_reduction", "tenure_extension", "moratorium_plus_extension"
        )
        assert len(result.rationale) > 0

    def test_stress_alerts_generated(self):
        from models.output_schema import RepaymentCadence, RiskBand
        from models.platform_schema import LoanAccount, TransactionSummary
        from orchestration.restructuring_advisor import generate_stress_alerts

        loan = LoanAccount(
            org_id=uuid.uuid4(),
            case_id=uuid.uuid4(),
            kirana_id=uuid.uuid4(),
            assessment_session_id=uuid.uuid4(),
            principal_amount=100000,
            tenure_months=12,
            repayment_cadence=RepaymentCadence.MONTHLY,
            annual_interest_rate_pct=18.0,
            processing_fee_pct=1.5,
            estimated_installment=10000,
            days_past_due=20,
            original_risk_band=RiskBand.HIGH,
        )

        current = TransactionSummary(
            total_credits=50000, total_debits=70000,
            credit_count=8, debit_count=15,
            avg_daily_balance=5000, period_days=30,
        )
        previous = TransactionSummary(
            total_credits=150000, total_debits=120000,
            credit_count=20, debit_count=30,
            avg_daily_balance=15000, period_days=30,
        )

        alerts = generate_stress_alerts(loan, current, previous)
        assert len(alerts) > 0
        assert any("past due" in a.lower() for a in alerts)


# ---------------------------------------------------------------------------
# 4. Loan Service Tests
# ---------------------------------------------------------------------------


class TestLoanService:
    """Tests for the loan_service module (requires repository setup)."""

    def test_loan_account_model_creation(self):
        """Verify LoanAccount model can be instantiated."""
        from models.output_schema import RepaymentCadence, RiskBand
        from models.platform_schema import LoanAccount, LoanAccountStatus

        loan = LoanAccount(
            org_id=uuid.uuid4(),
            case_id=uuid.uuid4(),
            kirana_id=uuid.uuid4(),
            assessment_session_id=uuid.uuid4(),
            status=LoanAccountStatus.ACTIVE,
            principal_amount=200000,
            tenure_months=18,
            repayment_cadence=RepaymentCadence.WEEKLY,
            annual_interest_rate_pct=18.0,
            processing_fee_pct=1.5,
            estimated_installment=3000,
            original_risk_band=RiskBand.MEDIUM,
        )

        assert loan.id is not None
        assert loan.status == LoanAccountStatus.ACTIVE
        assert loan.principal_amount == 200000
        assert loan.tenure_months == 18

    def test_monitoring_run_model_creation(self):
        """Verify MonitoringRun model can be instantiated."""
        from models.output_schema import RiskBand
        from models.platform_schema import MonitoringRun, MonitoringRunStatus

        run = MonitoringRun(
            org_id=uuid.uuid4(),
            case_id=uuid.uuid4(),
            loan_id=uuid.uuid4(),
            kirana_id=uuid.uuid4(),
            status=MonitoringRunStatus.COMPLETED,
            new_risk_band=RiskBand.HIGH,
            new_risk_score=0.62,
            alerts_raised=["Inflow dropped by 25%"],
        )

        assert run.id is not None
        assert run.status == MonitoringRunStatus.COMPLETED
        assert run.new_risk_band == RiskBand.HIGH


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

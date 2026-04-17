from uuid import UUID

import pytest

from analytics.cohort_analysis import build_cohort_analysis
from analytics.portfolio_metrics import build_portfolio_metrics
from models.platform_schema import CaseStatus, CaseStatusUpdateRequest, StatementUploadCreateRequest
from services.audit_service import AuditService
from services.case_service import CaseService
from services.compliance_exporter import ComplianceExporter
from services.document_builder import DocumentBuilder
from services.loan_service import LoanService
from services.monitoring_service import MonitoringService
from services.statement_parser import parse_statement_content
from storage.repository import PlatformRepository


@pytest.fixture
def services(tmp_path):
    repository = PlatformRepository(tmp_path / "platform")
    audit_service = AuditService(repository)
    loan_service = LoanService(repository, audit_service)
    case_service = CaseService(repository, audit_service, loan_service)
    monitoring_service = MonitoringService(repository, audit_service, loan_service)
    exporter = ComplianceExporter(DocumentBuilder(repository), audit_service)
    return repository, case_service, loan_service, monitoring_service, exporter


def test_invalid_status_transition_is_rejected(services):
    repository, case_service, _, _, _ = services
    case_id = UUID("63333333-3333-3333-3333-333333333333")  # submitted
    actor_id = UUID("22222222-2222-2222-2222-222222222222")

    with pytest.raises(ValueError, match="Invalid status transition"):
        case_service.update_case_status(
            case_id,
            CaseStatusUpdateRequest(actor_user_id=actor_id, new_status=CaseStatus.DISBURSED),
        )


def test_approval_and_disbursement_create_real_loan_artifacts(services):
    repository, case_service, loan_service, _, _ = services
    case_id = UUID("61111111-1111-1111-1111-111111111111")  # under_review
    actor_id = UUID("22222222-2222-2222-2222-222222222222")

    approved = case_service.update_case_status(
        case_id,
        CaseStatusUpdateRequest(
            actor_user_id=actor_id,
            new_status=CaseStatus.APPROVED,
            note="Approval test",
        ),
    )
    assert approved.case.status == CaseStatus.APPROVED
    assert repository.get_latest_loan_decision(case_id) is not None

    disbursed = case_service.update_case_status(
        case_id,
        CaseStatusUpdateRequest(
            actor_user_id=actor_id,
            new_status=CaseStatus.DISBURSED,
            note="Disbursement test",
        ),
    )
    assert disbursed.case.status == CaseStatus.DISBURSED
    account = repository.get_loan_account_for_case(case_id)
    assert account is not None
    assert account.principal_amount > 0
    detail = loan_service.get_loan_account_detail(case_id)
    assert detail.loan_account.case_id == case_id


def test_statement_upload_triggers_monitoring_and_documents(services):
    repository, _, _, monitoring_service, exporter = services
    case_id = UUID("62222222-2222-2222-2222-222222222222")
    actor_id = UUID("22222222-2222-2222-2222-222222222222")

    response = monitoring_service.upload_statement(
        case_id,
        StatementUploadCreateRequest(
            actor_user_id=actor_id,
            file_name="latest-cycle.csv",
            file_type="text/csv",
            source_kind="bank",
            content="date,description,amount,type\n2026-04-01,Supplier Traders,22000,debit\n2026-04-02,Customer UPI,48000,credit\n2026-04-03,Cash ATM,12000,debit\n2026-04-05,Counter sales,51000,credit\n",
        ),
    )
    assert response.statement_upload.transaction_count == 4
    assert response.monitoring_run.current_risk_band is not None
    assert repository.get_latest_monitoring_run(case_id) is not None

    bundle = exporter.export_case_bundle(case_id, actor_user_id=actor_id)
    assert "underwriting_summary" in bundle.payload
    assert bundle.bundle.case_id == case_id

    metrics = build_portfolio_metrics(repository, UUID("11111111-1111-1111-1111-111111111111"))
    cohorts = build_cohort_analysis(repository, UUID("11111111-1111-1111-1111-111111111111"))
    assert len(metrics) >= 6
    assert len(cohorts) >= 1


def test_pdf_style_upi_statement_text_is_parsed():
    parsed = parse_statement_content(
        file_name="paytm-apr-2026.pdf",
        file_type="application/pdf",
        content=(
            "12/04/2026 UPI CR Customer Payment INR 48,000\n"
            "13/04/2026 UPI DR Supplier Traders INR 22,000\n"
            "14/04/2026 UPI DR Cash Withdrawal INR 3,500\n"
        ),
    )

    assert parsed["transaction_count"] == 3
    assert parsed["inflow_total"] == 48000.0
    assert parsed["outflow_total"] == 25500.0

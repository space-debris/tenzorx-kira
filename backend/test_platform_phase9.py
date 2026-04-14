from uuid import UUID

from services.audit_service import AuditService
from services.case_service import CaseService
from storage.repository import PlatformRepository


def test_kirana_detail_aggregates_related_records():
    repository = PlatformRepository()
    service = CaseService(repository, AuditService(repository))

    org_id = UUID("11111111-1111-1111-1111-111111111111")
    kirana_id = UUID("32222222-2222-2222-2222-222222222222")

    detail = service.get_kirana_detail(org_id, kirana_id)

    assert detail.kirana.id == kirana_id
    assert len(detail.cases) >= 1
    assert len(detail.assessment_history) >= 1
    assert len(detail.loan_history) >= 1
    assert any(alert.kirana_id == kirana_id for alert in detail.alerts)

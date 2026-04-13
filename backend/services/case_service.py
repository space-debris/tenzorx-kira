"""
Case service for Phase 8 lender-platform workflows.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from models.platform_schema import (
    AlertStatus,
    AssessmentCase,
    AuditAction,
    AuditEntityType,
    CaseDetailResponse,
    CaseStatus,
    CaseStatusUpdateRequest,
    CreateCaseRequest,
    KiranaLocation,
    KiranaProfile,
    OrgDashboardResponse,
)
from services.audit_service import AuditService
from storage.repository import PlatformRepository


class CaseService:
    """Coordinates persistent case and kirana operations for lenders."""

    def __init__(self, repository: PlatformRepository, audit_service: AuditService) -> None:
        self.repository = repository
        self.audit_service = audit_service

    def create_case(self, payload: CreateCaseRequest) -> CaseDetailResponse:
        org = self.repository.get_organization(payload.org_id)
        if org is None:
            raise ValueError("Organization not found")

        created_by = self.repository.get_user(payload.created_by_user_id)
        if created_by is None or created_by.org_id != payload.org_id:
            raise ValueError("Creating user is invalid for this organization")

        if payload.assigned_to_user_id is not None:
            assigned_to = self.repository.get_user(payload.assigned_to_user_id)
            if assigned_to is None or assigned_to.org_id != payload.org_id:
                raise ValueError("Assigned user is invalid for this organization")

        latest_summary = None
        initial_status = CaseStatus.DRAFT
        if payload.assessment_session_id is not None:
            latest_summary = self.repository.get_assessment_summary(payload.assessment_session_id)
            if latest_summary is None:
                raise ValueError("Assessment session could not be found")
            initial_status = CaseStatus.UNDER_REVIEW

        now = datetime.utcnow()
        kirana = KiranaProfile(
            org_id=payload.org_id,
            store_name=payload.store_name,
            owner_name=payload.owner_name,
            owner_mobile=payload.owner_mobile,
            location=KiranaLocation(
                state=payload.state,
                district=payload.district,
                pin_code=payload.pin_code,
                locality=payload.locality,
            ),
            metadata=payload.metadata,
            created_at=now,
            updated_at=now,
        )
        self.repository.create_kirana(kirana)

        case = AssessmentCase(
            org_id=payload.org_id,
            kirana_id=kirana.id,
            created_by_user_id=payload.created_by_user_id,
            assigned_to_user_id=payload.assigned_to_user_id,
            status=initial_status,
            latest_assessment_session_id=(
                latest_summary.session_id if latest_summary is not None else None
            ),
            latest_assessment_id=(
                latest_summary.assessment_id if latest_summary is not None else None
            ),
            latest_risk_band=latest_summary.risk_band if latest_summary is not None else None,
            latest_loan_range=latest_summary.loan_range if latest_summary is not None else None,
            notes=payload.notes,
            created_at=now,
            updated_at=now,
        )
        self.repository.create_case(case)

        self.audit_service.record_event(
            org_id=payload.org_id,
            entity_type=AuditEntityType.KIRANA,
            entity_id=kirana.id,
            action=AuditAction.CREATED,
            description=f"Created kirana profile for {kirana.store_name}",
            actor_user_id=payload.created_by_user_id,
            metadata={"pin_code": kirana.location.pin_code},
        )
        self.audit_service.record_event(
            org_id=payload.org_id,
            entity_type=AuditEntityType.CASE,
            entity_id=case.id,
            action=AuditAction.CREATED,
            description=f"Created case for {kirana.store_name}",
            actor_user_id=payload.created_by_user_id,
            metadata={"status": case.status.value},
        )

        if latest_summary is not None:
            self.audit_service.record_event(
                org_id=payload.org_id,
                entity_type=AuditEntityType.ASSESSMENT,
                entity_id=latest_summary.assessment_id,
                action=AuditAction.ASSESSMENT_LINKED,
                description=f"Linked assessment {latest_summary.session_id} to case {case.id}",
                actor_user_id=payload.created_by_user_id,
                metadata={
                    "case_id": str(case.id),
                    "session_id": str(latest_summary.session_id),
                },
            )

        return self.get_case_detail(case.id)

    def link_assessment_to_case(
        self,
        case_id: uuid.UUID,
        session_id: uuid.UUID,
        actor_user_id: uuid.UUID | None = None,
    ) -> CaseDetailResponse:
        case = self.repository.get_case(case_id)
        if case is None:
            raise ValueError("Case not found")

        summary = self.repository.get_assessment_summary(session_id)
        if summary is None:
            raise ValueError("Assessment session could not be found")

        updated_case = case.model_copy(
            update={
                "latest_assessment_session_id": summary.session_id,
                "latest_assessment_id": summary.assessment_id,
                "latest_risk_band": summary.risk_band,
                "latest_loan_range": summary.loan_range,
                "status": (
                    CaseStatus.UNDER_REVIEW
                    if case.status == CaseStatus.DRAFT
                    else case.status
                ),
                "updated_at": datetime.utcnow(),
            }
        )
        self.repository.update_case(updated_case)

        self.audit_service.record_event(
            org_id=updated_case.org_id,
            entity_type=AuditEntityType.CASE,
            entity_id=updated_case.id,
            action=AuditAction.ASSESSMENT_LINKED,
            description=f"Linked assessment {summary.session_id} to case",
            actor_user_id=actor_user_id,
            metadata={"assessment_id": str(summary.assessment_id)},
        )
        return self.get_case_detail(case_id)

    def update_case_status(
        self,
        case_id: uuid.UUID,
        payload: CaseStatusUpdateRequest,
    ) -> CaseDetailResponse:
        case = self.repository.get_case(case_id)
        if case is None:
            raise ValueError("Case not found")

        actor = self.repository.get_user(payload.actor_user_id)
        if actor is None or actor.org_id != case.org_id:
            raise ValueError("Actor is invalid for this organization")

        updated_case = case.model_copy(
            update={
                "status": payload.new_status,
                "notes": payload.note or case.notes,
                "updated_at": datetime.utcnow(),
            }
        )
        self.repository.update_case(updated_case)

        self.audit_service.record_event(
            org_id=case.org_id,
            entity_type=AuditEntityType.CASE,
            entity_id=case.id,
            action=AuditAction.STATUS_CHANGED,
            description=f"Changed case status from {case.status.value} to {payload.new_status.value}",
            actor_user_id=payload.actor_user_id,
            metadata={
                "previous_status": case.status.value,
                "new_status": payload.new_status.value,
                "note": payload.note,
            },
        )
        return self.get_case_detail(case_id)

    def list_cases_for_org(self, org_id: uuid.UUID) -> list[AssessmentCase]:
        org = self.repository.get_organization(org_id)
        if org is None:
            raise ValueError("Organization not found")
        return self.repository.list_cases(org_id)

    def list_kiranas_for_org(self, org_id: uuid.UUID) -> list[KiranaProfile]:
        org = self.repository.get_organization(org_id)
        if org is None:
            raise ValueError("Organization not found")
        return self.repository.list_kiranas(org_id)

    def get_case_detail(self, case_id: uuid.UUID) -> CaseDetailResponse:
        case = self.repository.get_case(case_id)
        if case is None:
            raise ValueError("Case not found")

        kirana = self.repository.get_kirana(case.kirana_id)
        if kirana is None:
            raise ValueError("Kirana not found for case")

        latest_assessment = None
        if case.latest_assessment_session_id is not None:
            latest_assessment = self.repository.get_assessment_summary(
                case.latest_assessment_session_id
            )

        alerts = self.repository.list_alerts(case_id=case.id)
        audit_events = self.repository.list_audit_events(entity_id=case.id)
        audit_events.extend(self.repository.list_audit_events(entity_id=kirana.id))
        audit_events = sorted(
            {str(event.id): event for event in audit_events}.values(),
            key=lambda item: item.created_at,
            reverse=True,
        )

        return CaseDetailResponse(
            case=case,
            kirana=kirana,
            latest_assessment=latest_assessment,
            alerts=alerts,
            audit_events=audit_events,
        )

    def get_org_dashboard(self, org_id: uuid.UUID) -> OrgDashboardResponse:
        org = self.repository.get_organization(org_id)
        if org is None:
            raise ValueError("Organization not found")

        summary = self.repository.build_dashboard_summary(org_id)
        recent_cases = self.repository.list_cases(org_id)[:5]
        open_alerts = self.repository.list_alerts(
            org_id=org_id,
            status=AlertStatus.OPEN,
        )[:5]

        return OrgDashboardResponse(
            organization=org,
            summary=summary,
            recent_cases=recent_cases,
            open_alerts=open_alerts,
        )

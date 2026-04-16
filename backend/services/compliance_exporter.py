"""
Compliance export service for deterministic audit/document bundles.
"""

from __future__ import annotations

import uuid

from models.platform_schema import AuditAction, AuditEntityType, DocumentBundleResponse
from services.audit_service import AuditService
from services.document_builder import DocumentBuilder


class ComplianceExporter:
    """Generate and audit document/export requests."""

    def __init__(self, document_builder: DocumentBuilder, audit_service: AuditService) -> None:
        self.document_builder = document_builder
        self.audit_service = audit_service

    def export_case_bundle(
        self,
        case_id: uuid.UUID,
        actor_user_id: uuid.UUID | None = None,
    ) -> DocumentBundleResponse:
        bundle = self.document_builder.build_case_bundle(case_id, generated_by_user_id=actor_user_id)
        self.audit_service.record_event(
            org_id=bundle.bundle.org_id,
            entity_type=AuditEntityType.CASE,
            entity_id=case_id,
            action=AuditAction.EXPORTED,
            description="Exported deterministic case bundle",
            actor_user_id=actor_user_id,
            metadata={
                "document_bundle_id": str(bundle.bundle.id),
                "formats": bundle.bundle.export_formats,
            },
        )
        return bundle

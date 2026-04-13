"""
Audit service for Phase 8 platform actions.
"""

from __future__ import annotations

import uuid
from typing import Any

from models.platform_schema import AuditAction, AuditEntityType, AuditEvent
from storage.repository import PlatformRepository


class AuditService:
    """Thin service that records immutable platform audit events."""

    def __init__(self, repository: PlatformRepository) -> None:
        self.repository = repository

    def record_event(
        self,
        *,
        org_id: uuid.UUID,
        entity_type: AuditEntityType,
        entity_id: uuid.UUID,
        action: AuditAction,
        description: str,
        actor_user_id: uuid.UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        actor_name = None
        if actor_user_id is not None:
            actor = self.repository.get_user(actor_user_id)
            actor_name = actor.full_name if actor else None

        event = AuditEvent(
            org_id=org_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            description=description,
            actor_user_id=actor_user_id,
            actor_name=actor_name,
            metadata=metadata or {},
        )
        return self.repository.create_audit_event(event)

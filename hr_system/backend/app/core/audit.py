from datetime import datetime
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def log_event(
    db: AsyncSession,
    actor_user_id: Optional[int],
    action: str,
    entity: Optional[str] = None,
    entity_id: Optional[int] = None,
    meta: Optional[dict[str, Any]] = None,
):
    db.add(
        AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            meta=meta,
            created_at=datetime.utcnow(),
        )
    )
    # commit مش هنا — نخليه مع نفس transaction بتاعت الendpoint

from services.core.database import SessionLocal
from services.users.models.audit_log import AuditLog
from services.logs.utils import log_event


def write_audit(
    action: str,
    resource: str,
    *,
    user_id: str | None = None,
    resource_id: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    extra: str | None = None,
) -> None:
    try:
        db = SessionLocal()
    except Exception as exc:
        log_event("error", "audit", "db_session_failed", error=str(exc))
        return
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            ip=ip,
            user_agent=user_agent,
            extra=extra,
        )
        db.add(entry)
        db.commit()
    except Exception as exc:
        log_event("error", "audit", "write_failed", error=str(exc))
    finally:
        db.close()

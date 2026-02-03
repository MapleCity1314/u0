import sys

from services.core.database import SessionLocal
from services.logs.models.log import LogEntry


def log_event(
    level: str,
    module: str,
    message: str,
    *,
    request_id: str | None = None,
    error: str | None = None,
    extra: str | None = None,
) -> None:
    try:
        db = SessionLocal()
    except Exception as exc:
        print(f"[log_event] session_failed: {exc}", file=sys.stderr)
        return
    try:
        entry = LogEntry(
            level=level,
            module=module,
            request_id=request_id,
            message=message,
            error=error,
            extra=extra,
        )
        db.add(entry)
        db.commit()
    except Exception as exc:
        print(f"[log_event] write_failed: {exc}", file=sys.stderr)
    finally:
        db.close()

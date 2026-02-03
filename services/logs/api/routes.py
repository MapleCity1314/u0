from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from services.core.database import get_db
from services.logs.models.log import LogEntry
from services.logs.schemas import LogCreate, LogEntryOut

router = APIRouter()


@router.post("/logs", response_model=LogEntryOut)
def create_log(payload: LogCreate, db: Session = Depends(get_db)):
    try:
        entry = LogEntry(
            level=payload.level,
            module=payload.module,
            request_id=payload.request_id,
            message=payload.message,
            error=payload.error,
            extra=payload.extra,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"log_write_failed:{exc}")


@router.get("/logs", response_model=list[LogEntryOut])
def list_logs(
    level: str | None = None,
    module: str | None = None,
    request_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    try:
        query = db.query(LogEntry)
        if level:
            query = query.filter(LogEntry.level == level)
        if module:
            query = query.filter(LogEntry.module == module)
        if request_id:
            query = query.filter(LogEntry.request_id == request_id)
        return query.order_by(LogEntry.created_at.desc()).limit(limit).all()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"log_query_failed:{exc}")

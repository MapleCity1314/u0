from datetime import datetime
from pydantic import BaseModel


class LogEntryOut(BaseModel):
    id: int
    level: str
    module: str | None = None
    request_id: str | None = None
    message: str
    error: str | None = None
    extra: str | None = None
    created_at: datetime | None = None

    class Config:
        orm_mode = True


class LogCreate(BaseModel):
    level: str
    module: str | None = None
    request_id: str | None = None
    message: str
    error: str | None = None
    extra: str | None = None


class LogQuery(BaseModel):
    level: str | None = None
    module: str | None = None
    request_id: str | None = None
    limit: int = 100

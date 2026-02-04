from datetime import datetime
from pydantic import BaseModel, ConfigDict


class LogEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    level: str
    module: str | None = None
    request_id: str | None = None
    message: str
    error: str | None = None
    extra: str | None = None
    created_at: datetime | None = None


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

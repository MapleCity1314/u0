from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_id: str
    username: str
    status: str
    created_at: datetime | None = None


class RegisterRequest(BaseModel):
    invite_code: str
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    token: str
    expires_at: datetime
    user: UserOut


class InviteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    status: str
    used_count: int
    max_uses: int
    expires_at: datetime


class PositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    units: float | None = None
    cost: float | None = None
    amount: float | None = None
    opened_at: datetime | None = None
    source: str
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PositionCreate(BaseModel):
    code: str
    units: float | None = None
    cost: float | None = None
    amount: float | None = None
    opened_at: datetime | None = None


class PasswordUpdate(BaseModel):
    old_password: str
    new_password: str

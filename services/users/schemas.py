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


class WatchlistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str | None = None
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WatchlistCreate(BaseModel):
    code: str
    name: str | None = None


class WatchlistSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str | None = None
    nav: float | None = None
    nav_date: str | None = None
    since_added: float | None = None
    returns: dict


class PositionSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str | None = None
    amount: float | None = None
    nav: float | None = None
    nav_date: str | None = None
    daily_change: float | None = None
    daily_profit: float | None = None
    holding_profit: float | None = None
    total_profit: float | None = None
    entry_nav: float | None = None
    last_input_date: str | None = None
    updated_at: str | None = None
    updated_today: bool
    last_delta: float | None = None
    status: str


class PasswordUpdate(BaseModel):
    old_password: str
    new_password: str

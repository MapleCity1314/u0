from datetime import datetime
from pydantic import BaseModel


class UserOut(BaseModel):
    id: str
    display_id: str
    username: str
    status: str
    created_at: datetime | None = None

    class Config:
        orm_mode = True


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
    code: str
    status: str
    used_count: int
    max_uses: int
    expires_at: datetime

    class Config:
        orm_mode = True


class PositionOut(BaseModel):
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

    class Config:
        orm_mode = True


class PositionCreate(BaseModel):
    code: str
    units: float | None = None
    cost: float | None = None
    amount: float | None = None
    opened_at: datetime | None = None


class PasswordUpdate(BaseModel):
    old_password: str
    new_password: str

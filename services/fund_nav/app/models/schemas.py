from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str


class ApiResponse(BaseModel):
    ok: bool
    data: dict | list | str | int | float | None = None
    error: ErrorResponse | None = None


class RegisterRequest(BaseModel):
    invite_code: str
    username: str
    password: str
    name: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user_id: str
    name: str | None = None
    username: str | None = None
    avatar_url: str | None = None
    must_change_password: bool | None = None


class InviteCreateRequest(BaseModel):
    max_uses: int | None = None
    ttl_sec: int | None = None


class InviteResponse(BaseModel):
    code: str
    max_uses: int
    used: int
    remaining: int


class ProfileUpdateRequest(BaseModel):
    name: str | None = None
    avatar_url: str | None = None


class PasswordUpdateRequest(BaseModel):
    old_password: str
    new_password: str


class PositionUpdateRequest(BaseModel):
    units: float | None = None
    cost: float | None = None


class PositionResponse(BaseModel):
    code: str
    units: float
    cost: float | None = None


class PositionDetail(BaseModel):
    code: str
    name: str | None = None
    units: float
    cost: float | None = None
    last_nav: float | None = None
    market_value: float | None = None
    daily_return: float | None = None
    daily_pnl: float | None = None
    total_pnl: float | None = None


class FundSummary(BaseModel):
    code: str
    name: str | None = None
    est_return: float | None = None
    source: str | None = None


class FundEstimate(BaseModel):
    code: str
    name: str | None = None
    last_nav: float | None = None
    est_return: float | None = None
    est_nav: float | None = None
    source: str | None = None
    coverage: float | None = None


class WatchlistResponse(BaseModel):
    funds: list[FundSummary]

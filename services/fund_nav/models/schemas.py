from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str


class ApiResponse(BaseModel):
    ok: bool
    data: dict | list | str | int | float | None = None
    error: ErrorResponse | None = None


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
    preferred_source: str | None = None
    est_return_em: float | None = None
    est_nav_em: float | None = None
    source_em: str | None = None
    est_return_model: float | None = None
    est_nav_model: float | None = None
    source_model: str | None = None
    coverage_model: float | None = None

from datetime import datetime, timezone, timedelta
import os
import csv
import io

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, Query
import pandas as pd
from sqlalchemy.orm import Session

from services.core.database import get_db
from services.fund_nav.data import akshare_client as fund_data
from services.logs.utils import log_event
from services.modules.redis_cache import get_cache
from services.users.audit import write_audit
from services.users.config import INVITE_MAX_ACTIVE, LOCKOUT_DURATION_SEC, LOCKOUT_THRESHOLD
from services.users.models.invite import Invite
from services.users.models.position import Position
from services.users.models.position_event import PositionEvent
from services.users.models.session import SessionToken
from services.users.models.user import User
from services.users.models.watchlist_item import WatchlistItem
from services.users.schemas import (
    AuthResponse,
    InviteOut,
    LoginRequest,
    PasswordUpdate,
    PositionCreate,
    PositionOut,
    PositionSummaryOut,
    RegisterRequest,
    UserOut,
    WatchlistCreate,
    WatchlistOut,
    WatchlistSummaryOut,
)
from services.users.security import generate_token, hash_password, token_expires_at, verify_password
from services.users.utils import generate_display_id, generate_invite_code, invite_expires_at, token_hash

router = APIRouter()
_redis = get_cache()


def _cache_get_or_set(key: str, fetch, ttl: int) -> dict:
    if _redis is not None:
        return _redis.get_or_set(key, fetch, ttl=ttl)
    return fetch()


def _get_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    token_value = _get_token(authorization)
    if token_value is None:
        raise HTTPException(status_code=401, detail="missing_token")
    t_hash = token_hash(token_value)
    token = (
        db.query(SessionToken)
        .filter(SessionToken.token_hash == t_hash, SessionToken.revoked_at.is_(None))
        .first()
    )
    if token is None or token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="invalid_token")
    user = db.query(User).filter(User.id == token.user_id, User.status == "active").first()
    if user is None:
        raise HTTPException(status_code=401, detail="invalid_user")
    token.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return user


@router.post("/auth/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    try:
        invite = (
            db.query(Invite)
            .filter(Invite.code == payload.invite_code, Invite.status == "active")
            .first()
        )
        if invite is None or invite.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="invalid_invite")
        if invite.used_count >= invite.max_uses:
            raise HTTPException(status_code=400, detail="invite_used")

        if db.query(User).filter(User.username == payload.username).first():
            raise HTTPException(status_code=400, detail="username_exists")

        display_id = generate_display_id()
        while db.query(User).filter(User.display_id == display_id).first() is not None:
            display_id = generate_display_id()

        user = User(
            display_id=display_id,
            username=payload.username,
            password_hash=hash_password(payload.password),
        )
        db.add(user)
        db.flush()

        invite.used_count += 1
        invite.status = "used"

        token_value = generate_token()
        session = SessionToken(
            user_id=user.id,
            token_hash=token_hash(token_value),
            expires_at=token_expires_at(),
        )
        db.add(session)
        db.commit()
        db.refresh(user)

        write_audit("register", "user", user_id=str(user.id))

        return AuthResponse(
            token=token_value,
            expires_at=session.expires_at,
            user=UserOut.from_orm(user),
        )
    except HTTPException:
        raise
    except Exception as exc:
        log_event("error", "users.register", "register_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="register_failed")


@router.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.username == payload.username).first()
        if user is None:
            raise HTTPException(status_code=401, detail="invalid_credentials")

        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            raise HTTPException(status_code=403, detail="account_locked")

        if not verify_password(payload.password, user.password_hash):
            user.failed_login_count += 1
            if user.failed_login_count >= LOCKOUT_THRESHOLD:
                user.locked_until = datetime.now(timezone.utc) + timedelta(seconds=LOCKOUT_DURATION_SEC)
            db.commit()
            raise HTTPException(status_code=401, detail="invalid_credentials")

        user.failed_login_count = 0
        user.locked_until = None

        token_value = generate_token()
        session = SessionToken(
            user_id=user.id,
            token_hash=token_hash(token_value),
            expires_at=token_expires_at(),
        )
        db.add(session)
        db.commit()

        write_audit("login", "user", user_id=str(user.id))

        return AuthResponse(
            token=token_value,
            expires_at=session.expires_at,
            user=UserOut.from_orm(user),
        )
    except HTTPException:
        raise
    except Exception as exc:
        log_event("error", "users.login", "login_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="login_failed")


@router.post("/auth/logout")
def logout(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    token_value = _get_token(authorization)
    if token_value is None:
        raise HTTPException(status_code=401, detail="missing_token")
    t_hash = token_hash(token_value)
    session = (
        db.query(SessionToken)
        .filter(SessionToken.token_hash == t_hash, SessionToken.revoked_at.is_(None))
        .first()
    )
    if session is None:
        raise HTTPException(status_code=400, detail="session_not_found")
    session.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.from_orm(user)


@router.post("/auth/password")
def update_password(
    payload: PasswordUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="invalid_password")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    write_audit("password_update", "user", user_id=str(user.id))
    return {"ok": True}


@router.post("/invites", response_model=InviteOut)
def create_invite(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    active_count = (
        db.query(Invite)
        .filter(
            Invite.owner_id == user.id,
            Invite.status == "active",
            Invite.expires_at > datetime.now(timezone.utc),
        )
        .count()
    )
    if active_count >= INVITE_MAX_ACTIVE:
        raise HTTPException(status_code=400, detail="invite_limit_reached")

    code = generate_invite_code()
    while db.query(Invite).filter(Invite.code == code).first() is not None:
        code = generate_invite_code()

    try:
        invite = Invite(
            code=code,
            owner_id=user.id,
            expires_at=invite_expires_at(),
        )
        db.add(invite)
        db.commit()
        db.refresh(invite)

        write_audit("invite_create", "invite", user_id=str(user.id), resource_id=invite.code)

        return InviteOut.from_orm(invite)
    except Exception as exc:
        log_event("error", "users.invite", "invite_create_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="invite_create_failed")


@router.get("/invites", response_model=list[InviteOut])
def list_invites(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    invites = (
        db.query(Invite)
        .filter(Invite.owner_id == user.id)
        .order_by(Invite.created_at.desc())
        .all()
    )
    return [InviteOut.from_orm(i) for i in invites]


@router.delete("/invites/{code}")
def revoke_invite(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    invite = (
        db.query(Invite)
        .filter(Invite.owner_id == user.id, Invite.code == code)
        .first()
    )
    if invite is None:
        raise HTTPException(status_code=404, detail="invite_not_found")
    invite.status = "revoked"
    db.commit()
    write_audit("invite_revoke", "invite", user_id=str(user.id), resource_id=code)
    return {"ok": True}


@router.get("/positions", response_model=list[PositionOut])
def list_positions(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (
        db.query(Position)
        .filter(Position.user_id == user.id, Position.is_active.is_(True))
        .order_by(Position.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return [PositionOut.from_orm(row) for row in rows]


@router.post("/positions", response_model=PositionOut)
def upsert_position(
    payload: PositionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = (
        db.query(Position)
        .filter(Position.user_id == user.id, Position.code == payload.code, Position.is_active.is_(True))
        .first()
    )
    if row is None:
        now = datetime.now(timezone.utc)
        row = Position(
            user_id=user.id,
            code=payload.code,
            units=payload.units,
            cost=payload.cost,
            amount=payload.amount,
            opened_at=payload.opened_at or now,
            source="manual",
            is_active=True,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        event_type = "create"
        delta_units = payload.units
        delta_amount = payload.amount
        delta_cost = payload.cost
    else:
        prev_units = row.units or 0
        prev_amount = row.amount or 0
        delta_units = payload.units - prev_units if payload.units is not None else None
        delta_amount = payload.amount - prev_amount if payload.amount is not None else None
        delta_cost = payload.cost
        if payload.units is not None:
            row.units = payload.units
        if payload.cost is not None:
            row.cost = payload.cost
        if payload.amount is not None:
            row.amount = payload.amount
        if payload.opened_at is not None:
            row.opened_at = payload.opened_at
        if row.opened_at is None and payload.amount is not None:
            row.opened_at = datetime.now(timezone.utc)
        if payload.amount is not None and payload.amount <= 0:
            row.is_active = False
            row.deleted_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)
        db.commit()
        event_type = "update"

    event = PositionEvent(
        position_id=row.id,
        user_id=user.id,
        event_type=event_type,
        delta_units=delta_units,
        delta_amount=delta_amount,
        delta_cost=delta_cost,
    )
    db.add(event)
    db.commit()

    write_audit("position_upsert", "position", user_id=str(user.id), resource_id=str(row.id))

    return PositionOut.from_orm(row)


@router.delete("/positions/{code}")
def delete_position(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = (
        db.query(Position)
        .filter(Position.user_id == user.id, Position.code == code, Position.is_active.is_(True))
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="position_not_found")
    row.is_active = False
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()

    event = PositionEvent(
        position_id=row.id,
        user_id=user.id,
        event_type="delete",
    )
    db.add(event)
    db.commit()

    write_audit("position_delete", "position", user_id=str(user.id), resource_id=str(row.id))

    return {"ok": True}


@router.post("/positions/import/csv")
def import_positions_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        content = file.file.read().decode("utf-8")
    except Exception as exc:
        log_event("error", "users.positions", "csv_read_failed", error=str(exc))
        raise HTTPException(status_code=400, detail="csv_read_failed")
    reader = csv.DictReader(io.StringIO(content))
    required = {"code", "units", "cost", "amount", "trade_date"}
    if set(reader.fieldnames or []) != required:
        raise HTTPException(status_code=400, detail="invalid_headers")

    imported = 0
    for row in reader:
        code = row.get("code")
        if not code:
            continue
        units = float(row["units"]) if row.get("units") else None
        cost = float(row["cost"]) if row.get("cost") else None
        amount = float(row["amount"]) if row.get("amount") else None
        opened_at = None
        if row.get("trade_date"):
            try:
                opened_at = datetime.fromisoformat(row["trade_date"])
            except Exception:
                opened_at = None

        position = (
            db.query(Position)
            .filter(Position.user_id == user.id, Position.code == code, Position.is_active.is_(True))
            .first()
        )
        if position is None:
            position = Position(
                user_id=user.id,
                code=code,
                units=units,
                cost=cost,
                amount=amount,
                opened_at=opened_at,
                source="csv",
                is_active=True,
            )
            db.add(position)
            db.commit()
            db.refresh(position)
        else:
            prev_units = position.units or 0
            if units is not None:
                position.units = prev_units + units
            if amount is not None:
                position.amount = (position.amount or 0) + amount
            if cost is not None and units is not None:
                new_total_units = prev_units + units
                if new_total_units > 0:
                    position.cost = ((position.cost or 0) * prev_units + cost * units) / new_total_units
            if opened_at:
                position.opened_at = opened_at
            db.commit()

        event = PositionEvent(
            position_id=position.id,
            user_id=user.id,
            event_type="import",
            delta_units=units,
            delta_amount=amount,
            delta_cost=cost,
            payload=str(row),
        )
        db.add(event)
        db.commit()

        imported += 1

    write_audit("position_import", "position", user_id=str(user.id), extra=f"count={imported}")

    return {"ok": True, "imported": imported}


def _return_since(df: pd.DataFrame, target_date: pd.Timestamp) -> float | None:
    if df is None or df.empty:
        return None
    subset = df[df["date"] <= target_date]
    if subset.empty:
        return None
    last_nav = float(df["nav"].iloc[-1])
    base_nav = float(subset["nav"].iloc[-1])
    if base_nav <= 0:
        return None
    return (last_nav / base_nav) - 1.0


def _calc_fund_returns(code: str) -> dict:
    cache_key = f"fund:returns:{code}"
    ttl = int(os.getenv("FUND_NAV_RETURNS_TTL_SEC", "300"))

    def _compute():
        df = fund_data.get_fund_nav_daily(code)
        if df is None or df.empty:
            return {"nav": None, "nav_date": None, "returns": {}}
        df = df.sort_values("date")
        last_date = df["date"].iloc[-1]
        last_nav = float(df["nav"].iloc[-1])

        periods = {
            "week": 7,
            "month": 30,
            "quarter": 90,
            "halfYear": 180,
            "year1": 365,
            "year2": 365 * 2,
            "year3": 365 * 3,
            "year5": 365 * 5,
        }

        returns = {}
        for key, days in periods.items():
            returns[key] = _return_since(df, last_date - pd.Timedelta(days=days))

        ytd_start = pd.Timestamp(year=last_date.year, month=1, day=1)
        returns["ytd"] = _return_since(df, ytd_start)

        inception_nav = float(df["nav"].iloc[0])
        if inception_nav > 0:
            returns["inception"] = (last_nav / inception_nav) - 1.0
        else:
            returns["inception"] = None

        return {
            "nav": last_nav,
            "nav_date": last_date.strftime("%Y-%m-%d"),
            "returns": returns,
        }

    return _cache_get_or_set(cache_key, _compute, ttl=ttl)


def _calc_last_nav_and_daily(code: str) -> tuple[float | None, str | None, float | None]:
    cache_key = f"fund:last_nav:{code}"
    ttl = int(os.getenv("FUND_NAV_LAST_NAV_TTL_SEC", "120"))

    def _compute():
        df = fund_data.get_fund_nav_daily(code)
        if df is None or df.empty:
            return {"nav": None, "nav_date": None, "daily_change": None}
        df = df.sort_values("date")
        last_nav = float(df["nav"].iloc[-1])
        last_date = df["date"].iloc[-1].strftime("%Y-%m-%d")
        if len(df) < 2:
            return {"nav": last_nav, "nav_date": last_date, "daily_change": None}
        prev_nav = float(df["nav"].iloc[-2])
        if prev_nav <= 0:
            return {"nav": last_nav, "nav_date": last_date, "daily_change": None}
        daily_change = (last_nav / prev_nav) - 1.0
        return {"nav": last_nav, "nav_date": last_date, "daily_change": daily_change}

    payload = _cache_get_or_set(cache_key, _compute, ttl=ttl)
    return payload["nav"], payload["nav_date"], payload["daily_change"]


def _calc_nav_on_or_before(code: str, date_str: str) -> float | None:
    cache_key = f"fund:nav_at:{code}:{date_str}"
    ttl = int(os.getenv("FUND_NAV_NAV_AT_TTL_SEC", "3600"))

    def _compute():
        df = fund_data.get_fund_nav_daily(code)
        if df is None or df.empty:
            return {"nav": None}
        df = df.sort_values("date")
        target = pd.Timestamp(date_str)
        subset = df[df["date"] <= target]
        if subset.empty:
            return {"nav": None}
        nav = float(subset["nav"].iloc[-1])
        return {"nav": nav}

    payload = _cache_get_or_set(cache_key, _compute, ttl=ttl)
    return payload["nav"]


def _latest_trading_date() -> str:
    cache_key = "trade:latest:CN"
    ttl = int(os.getenv("FUND_NAV_TRADE_CAL_TTL_SEC", "300"))

    def _compute():
        return {"date": fund_data.get_latest_trading_date()}

    payload = _cache_get_or_set(cache_key, _compute, ttl=ttl)
    return payload["date"]


def _lookup_fund_name(code: str) -> str | None:
    cache_key = f"fund:name:{code}"
    ttl = int(os.getenv("FUND_NAV_FUND_NAME_TTL_SEC", "3600"))

    def _compute():
        df = fund_data.get_fund_value_estimation()
        if df is None or df.empty:
            return {"name": None}
        code_col = None
        name_col = None
        for c in df.columns:
            if "基金代码" in c or c.lower() in ("code", "基金代码"):
                code_col = c
            if "基金名称" in c or c.lower() in ("name", "基金名称"):
                name_col = c
        if code_col is None or name_col is None:
            return {"name": None}
        row = df[df[code_col].astype(str) == str(code)]
        if row.empty:
            return {"name": None}
        return {"name": str(row.iloc[0][name_col])}

    payload = _cache_get_or_set(cache_key, _compute, ttl=ttl)
    return payload["name"]


@router.get("/watchlist", response_model=list[WatchlistOut])
def list_watchlist(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == user.id, WatchlistItem.is_active.is_(True))
        .order_by(WatchlistItem.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return [WatchlistOut.from_orm(row) for row in rows]


@router.get("/watchlist/summary", response_model=list[WatchlistSummaryOut])
def list_watchlist_summary(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == user.id, WatchlistItem.is_active.is_(True))
        .order_by(WatchlistItem.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    out = []
    for row in rows:
        payload = _calc_fund_returns(row.code)
        since_added = None
        if row.created_at and payload["nav"] is not None:
            base_nav = _calc_nav_on_or_before(row.code, row.created_at.strftime("%Y-%m-%d"))
            if base_nav and base_nav > 0:
                since_added = float(payload["nav"]) / float(base_nav) - 1.0
        out.append(
            WatchlistSummaryOut(
                id=row.id,
                code=row.code,
                name=row.name,
                nav=payload["nav"],
                nav_date=payload["nav_date"],
                since_added=since_added,
                returns=payload["returns"],
            )
        )
    return out


@router.post("/watchlist", response_model=WatchlistOut)
def upsert_watchlist(
    payload: WatchlistCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    code = payload.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="invalid_code")

    row = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == user.id, WatchlistItem.code == code, WatchlistItem.is_active.is_(True))
        .first()
    )
    if row is None:
        row = (
            db.query(WatchlistItem)
            .filter(WatchlistItem.user_id == user.id, WatchlistItem.code == code, WatchlistItem.is_active.is_(False))
            .first()
        )
        if row is None:
            row = WatchlistItem(
                user_id=user.id,
                code=code,
                name=payload.name,
                is_active=True,
            )
            db.add(row)
        else:
            row.is_active = True
            row.deleted_at = None
            if payload.name:
                row.name = payload.name
        db.commit()
        db.refresh(row)
        write_audit("watchlist_add", "watchlist", user_id=str(user.id), resource_id=str(row.id))
        return WatchlistOut.from_orm(row)

    if payload.name:
        row.name = payload.name
        db.commit()
        db.refresh(row)
    return WatchlistOut.from_orm(row)


@router.delete("/watchlist/{code}")
def delete_watchlist(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    code = code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="invalid_code")
    row = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == user.id, WatchlistItem.code == code, WatchlistItem.is_active.is_(True))
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="watchlist_not_found")
    row.is_active = False
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()
    write_audit("watchlist_delete", "watchlist", user_id=str(user.id), resource_id=str(row.id))
    return {"ok": True}


@router.get("/positions/summary", response_model=list[PositionSummaryOut])
def list_positions_summary(
    include_inactive: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Position).filter(Position.user_id == user.id)
    if not include_inactive:
        query = query.filter(Position.is_active.is_(True))
    rows = query.order_by(Position.created_at.desc()).limit(limit).offset(offset).all()

    latest_trade_date = _latest_trading_date()
    out = []
    for row in rows:
        nav, nav_date, daily_change = _calc_last_nav_and_daily(row.code)
        name = _lookup_fund_name(row.code)
        amount = row.amount
        entry_nav = None
        if row.cost is not None:
            entry_nav = float(row.cost)
        elif row.units and row.units > 0 and amount is not None:
            entry_nav = float(amount) / float(row.units)
        elif row.opened_at:
            entry_nav = _calc_nav_on_or_before(row.code, row.opened_at.strftime("%Y-%m-%d"))

        daily_profit = None
        holding_profit = None
        total_profit = None
        if amount is not None and daily_change is not None:
            daily_profit = float(amount) * float(daily_change)
        if amount is not None and nav is not None and entry_nav:
            holding_profit = float(amount) * (float(nav) / float(entry_nav) - 1.0)
            total_profit = holding_profit

        last_event = (
            db.query(PositionEvent)
            .filter(PositionEvent.position_id == row.id, PositionEvent.user_id == user.id)
            .order_by(PositionEvent.created_at.desc())
            .first()
        )
        last_delta = None
        if last_event and last_event.delta_amount is not None:
            last_delta = float(last_event.delta_amount)

        last_input = row.updated_at or row.opened_at or row.created_at
        last_input_date = last_input.strftime("%Y-%m-%d") if last_input else None
        updated_at = row.updated_at.strftime("%Y-%m-%d %H:%M") if row.updated_at else None
        updated_today = nav_date == latest_trade_date if nav_date else False

        status = "持有"
        if not row.is_active or (amount is not None and amount <= 0):
            status = "已清仓"

        out.append(
            PositionSummaryOut(
                id=row.id,
                code=row.code,
                name=name,
                amount=amount,
                nav=nav,
                nav_date=nav_date,
                daily_change=daily_change,
                daily_profit=daily_profit,
                holding_profit=holding_profit,
                total_profit=total_profit,
                entry_nav=entry_nav,
                last_input_date=last_input_date,
                updated_at=updated_at,
                updated_today=updated_today,
                last_delta=last_delta,
                status=status,
            )
        )
    return out

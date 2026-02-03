from datetime import datetime, timezone, timedelta
import csv
import io

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from sqlalchemy.orm import Session

from services.core.database import get_db
from services.logs.utils import log_event
from services.users.audit import write_audit
from services.users.config import INVITE_MAX_ACTIVE, LOCKOUT_DURATION_SEC, LOCKOUT_THRESHOLD
from services.users.models.invite import Invite
from services.users.models.position import Position
from services.users.models.position_event import PositionEvent
from services.users.models.session import SessionToken
from services.users.models.user import User
from services.users.schemas import (
    AuthResponse,
    InviteOut,
    LoginRequest,
    PasswordUpdate,
    PositionCreate,
    PositionOut,
    RegisterRequest,
    UserOut,
)
from services.users.security import generate_token, hash_password, token_expires_at, verify_password
from services.users.utils import generate_display_id, generate_invite_code, invite_expires_at, token_hash

router = APIRouter()


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
def list_positions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        db.query(Position)
        .filter(Position.user_id == user.id, Position.is_active.is_(True))
        .order_by(Position.created_at.desc())
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
        row = Position(
            user_id=user.id,
            code=payload.code,
            units=payload.units,
            cost=payload.cost,
            amount=payload.amount,
            opened_at=payload.opened_at,
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
        delta_units = payload.units
        delta_amount = payload.amount
        delta_cost = payload.cost
        if payload.units is not None:
            row.units = payload.units
        if payload.cost is not None:
            row.cost = payload.cost
        if payload.amount is not None:
            row.amount = payload.amount
        if payload.opened_at is not None:
            row.opened_at = payload.opened_at
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

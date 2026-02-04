from datetime import datetime, timezone

from services.users.models.invite import Invite
from services.users.models.session import SessionToken
from services.users.models.user import User
from services.users.security import generate_token, hash_password, token_expires_at
from services.users.utils import generate_display_id, invite_expires_at, token_hash


def _seed_user(db_session, username: str, password: str) -> tuple[User, str]:
    user = User(
        display_id=generate_display_id(),
        username=username,
        password_hash=hash_password(password),
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token_value = generate_token()
    session = SessionToken(
        user_id=user.id,
        token_hash=token_hash(token_value),
        expires_at=token_expires_at(),
    )
    db_session.add(session)
    db_session.commit()

    return user, token_value


def test_user_auth_and_positions(client, db_session):
    _, token_value = _seed_user(db_session, "admin", "admin-pass")
    headers = {"Authorization": f"Bearer {token_value}"}

    resp = client.post("/api/invites", headers=headers)
    assert resp.status_code == 200
    invite_code = resp.json()["code"]

    resp = client.post(
        "/api/auth/register",
        json={"invite_code": invite_code, "username": "alice", "password": "pass123"},
    )
    assert resp.status_code == 200
    register_token = resp.json()["token"]

    resp = client.post("/api/auth/login", json={"username": "alice", "password": "pass123"})
    assert resp.status_code == 200
    login_token = resp.json()["token"]

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {login_token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "alice"

    resp = client.post(
        "/api/auth/password",
        headers={"Authorization": f"Bearer {login_token}"},
        json={"old_password": "pass123", "new_password": "pass456"},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    resp = client.post(
        "/api/positions",
        headers={"Authorization": f"Bearer {login_token}"},
        json={"code": "110022", "units": 10, "cost": 1.2, "amount": 12.0},
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == "110022"

    resp = client.get("/api/positions", headers={"Authorization": f"Bearer {login_token}"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    csv_body = "code,units,cost,amount,trade_date\n110022,5,1.1,5.5,2024-01-01\n"
    resp = client.post(
        "/api/positions/import/csv",
        headers={"Authorization": f"Bearer {login_token}"},
        files={"file": ("positions.csv", csv_body, "text/csv")},
    )
    assert resp.status_code == 200
    assert resp.json()["imported"] == 1

    resp = client.delete("/api/positions/110022", headers={"Authorization": f"Bearer {login_token}"})
    assert resp.status_code == 200

    resp = client.get("/api/positions", headers={"Authorization": f"Bearer {login_token}"})
    assert resp.status_code == 200
    assert resp.json() == []

    resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {login_token}"})
    assert resp.status_code == 200


def test_register_rejects_invalid_invite(client):
    resp = client.post(
        "/api/auth/register",
        json={"invite_code": "INVALID", "username": "bob", "password": "pass"},
    )
    assert resp.status_code == 400


def test_invite_expired(client, db_session):
    user, _ = _seed_user(db_session, "seed", "seed-pass")
    invite = Invite(
        code="IVEXPIRED",
        owner_id=user.id,
        expires_at=datetime.now(timezone.utc),
        status="active",
    )
    db_session.add(invite)
    db_session.commit()

    resp = client.post(
        "/api/auth/register",
        json={"invite_code": "IVEXPIRED", "username": "carol", "password": "pass"},
    )
    assert resp.status_code == 400

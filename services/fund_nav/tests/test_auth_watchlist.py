import importlib
import os

from fastapi.testclient import TestClient


def _build_client(tmp_path):
    os.environ["FUND_NAV_STORE_BACKEND"] = "sqlite"
    os.environ["FUND_NAV_DB_PATH"] = str(tmp_path / "fund_nav_test.db")
    os.environ["FUND_NAV_INITIAL_INVITE_CODE"] = "TESTCODE"

    app_module = importlib.import_module("services.fund_nav.app.main")
    importlib.reload(app_module)
    return TestClient(app_module.app)


def test_invite_register_and_watchlist(tmp_path):
    client = _build_client(tmp_path)

    res = client.post(
        "/api/auth/register",
        json={
            "invite_code": "TESTCODE",
            "username": "demo",
            "password": "pass1234",
            "name": "demo",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    token = body["data"]["token"]

    res = client.post(
        "/api/auth/invites",
        headers={"Authorization": f"Bearer {token}"},
        json={"max_uses": 2},
    )
    assert res.status_code == 200
    invite_code = res.json()["data"]["code"]

    res = client.post(
        "/api/auth/register",
        json={
            "invite_code": invite_code,
            "username": "demo2",
            "password": "pass5678",
            "name": "demo2",
        },
    )
    assert res.status_code == 200

    res = client.post(
        "/api/auth/login",
        json={"username": "demo2", "password": "pass5678"},
    )
    assert res.status_code == 200

    res = client.post(
        "/api/watchlist/022485",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200

    res = client.get(
        "/api/watchlist/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["ok"] is True

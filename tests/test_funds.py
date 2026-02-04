import pandas as pd

from services.fund_nav.api import funds as funds_api


def test_fund_search_and_detail(client, monkeypatch):
    df = pd.DataFrame(
        [
            {"code": "123456", "name": "Demo Fund"},
            {"code": "654321", "name": "Other Fund"},
        ]
    )

    def fake_estimation():
        return df

    def fake_estimate_fund(code: str, index_code=None, source="auto"):
        return {
            "code": code,
            "name": "Demo Fund",
            "last_nav": 1.0,
            "est_return": 0.01,
            "est_nav": 1.01,
            "source": "model",
            "coverage": 0.9,
            "preferred_source": "model",
            "est_return_em": None,
            "est_nav_em": None,
            "source_em": None,
            "est_return_model": 0.01,
            "est_nav_model": 1.01,
            "source_model": "model",
            "coverage_model": 0.9,
        }

    monkeypatch.setattr(funds_api.data, "get_fund_value_estimation", fake_estimation)
    monkeypatch.setattr(funds_api.data, "estimate_fund", fake_estimate_fund)
    monkeypatch.setattr(
        funds_api.data,
        "get_fund_nav_recent",
        lambda code, days=7: pd.DataFrame(
            [{"date": pd.Timestamp("2024-01-01"), "nav": 1.0}]
        ),
    )
    monkeypatch.setattr(
        funds_api.data,
        "estimate_curve",
        lambda code, history: [{"date": "2024-01-01", "nav": 1.0}],
    )

    resp = client.get("/api/funds/search", params={"q": "123"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"][0]["code"] == "123456"

    resp = client.get("/api/funds/123456")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["code"] == "123456"

    resp = client.get("/api/funds/123456/curve", params={"days": 7})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"][0]["date"] == "2024-01-01"

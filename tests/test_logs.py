def test_logs_create_and_list(client):
    payload = {
        "level": "info",
        "module": "tests",
        "request_id": "req-1",
        "message": "hello",
        "error": None,
        "extra": "meta",
    }
    resp = client.post("/api/logs", json=payload)
    assert resp.status_code == 200
    created = resp.json()
    assert created["level"] == "info"
    assert created["module"] == "tests"

    resp = client.get("/api/logs", params={"level": "info", "limit": 10})
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    assert len(items) >= 1

from datetime import datetime, timezone

from sqlalchemy import func

from services.news.models.news import NewsItem


def test_news_list_and_query(client, db_session):
    item1 = NewsItem(
        source="demo",
        market="cn",
        title="hello market",
        url="https://example.com/news/1",
        summary="summary text",
        tags="test",
        fingerprint="fp-1",
        published_at=datetime.now(timezone.utc),
        search_vector=func.to_tsvector("simple", "hello market summary"),
    )
    item2 = NewsItem(
        source="demo",
        market="cn",
        title="second item",
        url="https://example.com/news/2",
        summary="more text",
        tags="test",
        fingerprint="fp-2",
        published_at=datetime.now(timezone.utc),
        search_vector=func.to_tsvector("simple", "second item more"),
    )
    item3 = NewsItem(
        source="demo",
        market="cn",
        title="third item",
        url="https://example.com/news/3",
        summary="third text",
        tags="test",
        fingerprint="fp-3",
        published_at=datetime.now(timezone.utc),
        search_vector=func.to_tsvector("simple", "third item"),
    )
    db_session.add_all([item1, item2, item3])
    db_session.commit()

    resp = client.get("/api/news", params={"limit": 5})
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 3

    resp = client.get("/api/news", params={"q": "hello"})
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["title"] == "hello market"

    resp = client.get("/api/news", params={"limit": 2})
    assert resp.status_code == 200
    page1 = resp.json()
    assert len(page1) == 2
    cursor = page1[-1]["id"]

    resp = client.get("/api/news", params={"limit": 2, "cursor": cursor})
    assert resp.status_code == 200
    page2 = resp.json()
    assert len(page2) == 1

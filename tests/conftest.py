import os
import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from services.core.base import Base


TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://murde@127.0.0.1:5432/u0_test",
)


def _import_all_models() -> None:
    import importlib
    import pkgutil

    import services

    for module_info in pkgutil.walk_packages(services.__path__, services.__name__ + "."):
        name = module_info.name
        if name.endswith(".models") or ".models." in name:
            importlib.import_module(name)


def _ensure_database(db_url: str) -> None:
    url = make_url(db_url)
    db_name = url.database or ""
    admin_db = os.getenv("POSTGRES_ADMIN_DB", "postgres")
    admin_url = url.set(drivername="postgresql", database=admin_db)
    try:
        with psycopg.connect(
            admin_url.render_as_string(hide_password=False), autocommit=True
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (db_name,))
                if cur.fetchone() is None:
                    cur.execute(f'CREATE DATABASE "{db_name}"')
    except Exception as exc:
        raise RuntimeError(f"Failed to ensure test database {db_name}: {exc}") from exc


@pytest.fixture(scope="session")
def db_engine():
    _ensure_database(TEST_DATABASE_URL)
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True, future=True)
    _import_all_models()
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def db_session(db_engine):
    SessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    with db_engine.begin() as conn:
        tables = conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        ).scalars().all()
        if tables:
            quoted = ", ".join(f'"{name}"' for name in tables)
            conn.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def app(db_engine):
    from services.core import database
    from services.fund_nav.api import funds as funds_api
    from services.logs.api import routes as logs_routes
    from services.news.api import routes as news_routes
    from services.news.api import sse as news_sse
    from services.users.api import routes as users_routes

    SessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    database.SessionLocal = SessionLocal

    def get_db_override():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    test_app = FastAPI()
    test_app.include_router(funds_api.router, prefix="/api/funds", tags=["funds"])
    test_app.include_router(news_routes.router, prefix="/api", tags=["news"])
    test_app.include_router(news_sse.router, prefix="/api", tags=["news"])
    test_app.include_router(logs_routes.router, prefix="/api", tags=["logs"])
    test_app.include_router(users_routes.router, prefix="/api", tags=["users"])
    test_app.dependency_overrides[database.get_db] = get_db_override

    @test_app.get("/health")
    def health():
        return {"ok": True}

    return test_app


@pytest.fixture()
def client(app):
    return TestClient(app)

"""Pytest configuration: in-memory SQLite, fresh schema per test, httpx async client."""

from __future__ import annotations

import os
import sys
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

# Single shared in-memory SQLite (default :memory: would be empty per connection).
_DEFAULT_TEST_DB = "sqlite+pysqlite:///:memory:"
os.environ["DATABASE_URL"] = os.environ.get("PYTEST_DATABASE_URL", _DEFAULT_TEST_DB)
# Tests use SQLite; never treat the process as production (local .env may set production).
os.environ["ENVIRONMENT"] = "test"
os.environ.setdefault("SECRET_KEY", "pytest-secret-key-must-be-long-enough-32")
os.environ.setdefault("ALLOWED_ORIGINS", "http://127.0.0.1:5173")

_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

import app.models  # noqa: E402, F401 — register models on Base.metadata
import httpx  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402


def _make_test_engine(url: str):
    if url.startswith("sqlite"):
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(url)


def pytest_runtest_setup(item: pytest.Item) -> None:
    if not any(m.name == "postgres" for m in item.iter_markers()):
        return
    url = os.environ.get("DATABASE_URL", "")
    if "postgresql" not in url and "postgres" not in url:
        pytest.skip(
            "Postgres tests: set PYTEST_DATABASE_URL to a postgresql+psycopg2 (or postgresql) URL, "
            "e.g. postgresql+psycopg2://user:pass@localhost:5432/medical_test, then: pytest -m postgres"
        )


@pytest.fixture(autouse=True)
def _reset_database() -> Iterator[None]:
    """Isolate each test with a clean schema."""
    from app.core import database as db_module

    engine = _make_test_engine(os.environ["DATABASE_URL"])
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db_module.engine = engine
    db_module.SessionLocal = TestingSessionLocal

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    session = TestingSessionLocal()
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session() -> Iterator[Session]:
    """DB session bound to the per-test engine (see _reset_database)."""
    from app.core import database as db_module

    db = db_module.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

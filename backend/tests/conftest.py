import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("EXPOSE_RESET_TOKEN", "true")

import pytest
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.database.database import SessionLocal, engine
from app.models.base import Base


@pytest.fixture
def db() -> Session:
    Base.metadata.create_all(engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)

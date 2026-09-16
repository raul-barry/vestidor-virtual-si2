import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["EXPOSE_RESET_TOKEN"] = "true"

import pytest
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.database.database import SessionLocal, engine
from app.models.base import Base


def session_token(db, data):
    from datetime import datetime, timedelta, timezone
    from app.core.security import create_access_token
    from app.models.sesion import Sesion
    token = create_access_token(data)
    now = datetime.now(timezone.utc)
    db.add(Sesion(id_usuario=data["id_usuario"], token_jwt=token,
                 fecha_inicio=now, fecha_expiracion=now + timedelta(minutes=30), estado="ACTIVA"))
    db.commit()
    return token


@pytest.fixture
def db() -> Session:
    Base.metadata.create_all(engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)

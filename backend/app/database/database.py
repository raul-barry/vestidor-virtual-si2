from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.models.base import Base

engine_options = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    engine_options.update({"connect_args": {"check_same_thread": False}, "poolclass": StaticPool})

engine = create_engine(settings.database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

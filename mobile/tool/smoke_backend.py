"""Isolated live backend for mobile contract tests; never uses a real database."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SECRET_KEY"] = "isolated-mobile-contract-test-key-not-for-deployment"
os.environ["ENVIRONMENT"] = "test"
os.environ["CORS_ORIGINS"] = "http://localhost:8765,http://127.0.0.1:8765"
from app.main import app
from app.database.database import engine, SessionLocal
from app.models.base import Base
from app.database.seed import seed_initial_data

Base.metadata.create_all(engine)
with SessionLocal() as db:
    seed_initial_data(db)
    db.commit()

@app.get("/__mobile_smoke")
def isolated_marker():
    return {"environment": "isolated-mobile-smoke"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8766, log_level="warning")

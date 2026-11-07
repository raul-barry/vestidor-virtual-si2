"""Secure, idempotent bootstrap for the first platform administrator."""

import getpass
import os
import sys
import traceback

from sqlalchemy.exc import SQLAlchemyError

from app.database.database import SessionLocal
from app.services.platform_admin_bootstrap import bootstrap_platform_admin


def _write_safe_traceback(exc: Exception) -> None:
    """Print stack frames without SQL parameters, credentials, or connection URLs."""
    print("Platform administrator bootstrap failed:", file=sys.stderr)
    for frame in traceback.extract_tb(exc.__traceback__):
        print(f'  File "{frame.filename}", line {frame.lineno}, in {frame.name}', file=sys.stderr)

    if isinstance(exc, SQLAlchemyError):
        # SQLAlchemy exception strings can include bound values (including hashes)
        # and connection details. Keep the exception class, omit those details.
        message = "database operation failed; SQL parameters and connection details omitted"
    else:
        message = str(exc)
        for secret_name in ("PLATFORM_ADMIN_PASSWORD", "DATABASE_URL"):
            secret = os.getenv(secret_name)
            if secret:
                message = message.replace(secret, "[REDACTED]")
    print(f"{type(exc).__name__}: {message}", file=sys.stderr)


def main() -> None:
    db = None
    try:
        email = os.getenv("PLATFORM_ADMIN_EMAIL") or input("Platform administrator email: ").strip()
        password = os.getenv("PLATFORM_ADMIN_PASSWORD") or getpass.getpass("Platform administrator password: ")
        db = SessionLocal()
        user, created = bootstrap_platform_admin(db, email, password)
        db.commit()
        print(f"Platform administrator {'created' if created else 'already initialized'}: {user.correo} (user id {user.id_usuario})")
    except Exception as exc:
        if db is not None:
            try:
                db.rollback()
            except Exception:
                print("Rollback failed; database error details omitted.", file=sys.stderr)
        _write_safe_traceback(exc)
        raise SystemExit(1) from None
    finally:
        if db is not None:
            try:
                db.close()
            except Exception:
                print("Session close failed; database error details omitted.", file=sys.stderr)


if __name__ == "__main__":
    main()

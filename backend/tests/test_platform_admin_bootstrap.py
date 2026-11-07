import pytest

from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import get_current_user, verify_password, verify_token
from app.database.seed import seed_roles
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.schemas.auth import LoginRequest
from app.services.auth_service import AuthService
from app.services.platform_admin_bootstrap import bootstrap_platform_admin
from app.database import bootstrap_platform_admin as bootstrap_command


def test_bootstrap_creates_one_global_platform_admin_and_is_idempotent(db):
    email = "platform.owner@example.test"
    password = "A-private-demo-passphrase-238!"

    user, created = bootstrap_platform_admin(db, email, password)
    db.commit()
    user_id = user.id_usuario
    assert created is True
    assert user.id_organizacion is None
    assert user.rol.nombre == "ADMINISTRADOR_PLATAFORMA"
    assert verify_password(password, user.password_hash)
    assert password not in user.password_hash

    existing, created_again = bootstrap_platform_admin(db, email, "Different-passphrase-239!")
    assert created_again is False
    assert existing.id_usuario == user_id
    assert verify_password(password, existing.password_hash)
    assert db.scalar(select(Usuario.id_usuario).where(Usuario.rol.has(Rol.nombre == "ADMINISTRADOR_PLATAFORMA"))) == user_id


def test_global_platform_admin_can_login_without_an_organization(db):
    email = "platform.login@example.test"
    password = "Another-private-passphrase-240!"
    user, _ = bootstrap_platform_admin(db, email, password)
    db.commit()

    token, authenticated = AuthService(db).login_user(LoginRequest(correo=email, password=password))
    assert authenticated.id_organizacion is None
    assert verify_token(token)["id_organizacion"] is None

    current = get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token), db)
    assert current.id_usuario == user.id_usuario
    assert "organization_id" not in db.info


def test_bootstrap_rejects_invalid_password_and_does_not_escalate_existing_company_user(db):
    seed_roles(db)
    db.flush()
    company_admin_role = db.scalar(select(Rol).where(Rol.nombre == "ADMINISTRADOR"))
    company_admin = Usuario(
        id_organizacion=1, id_rol=company_admin_role.id_rol, nombres="Company", apellidos="Admin",
        correo="company.admin@example.test", password_hash="existing-hash", estado="ACTIVO",
    )
    db.add(company_admin)
    db.flush()

    with pytest.raises(ValueError, match="at least 12"):
        bootstrap_platform_admin(db, "new.platform@example.test", "short")
    with pytest.raises(ValueError, match="different account"):
        bootstrap_platform_admin(db, company_admin.correo, "Long-private-passphrase-241!")
    assert company_admin.rol.nombre == "ADMINISTRADOR"


def test_bootstrap_rejects_duplicate_email_owned_by_company_user(db):
    seed_roles(db)
    role = db.scalar(select(Rol).where(Rol.nombre == "ADMINISTRADOR"))
    existing = Usuario(
        id_organizacion=1, id_rol=role.id_rol, nombres="Existing", apellidos="User",
        correo="duplicate@example.test", password_hash="existing-hash", estado="ACTIVO",
    )
    db.add(existing)
    db.flush()

    with pytest.raises(ValueError, match="already belongs to a different account"):
        bootstrap_platform_admin(db, existing.correo, "Long-private-passphrase-242!")


def test_bootstrap_rejects_missing_global_role(db, monkeypatch):
    monkeypatch.setattr("app.services.platform_admin_bootstrap.seed_roles", lambda _db: 0)

    with pytest.raises(ValueError, match="role is unavailable"):
        bootstrap_platform_admin(db, "missing.role@example.test", "Long-private-passphrase-243!")


def test_bootstrap_rejects_malformed_email(db):
    with pytest.raises(ValueError, match="valid administrator email"):
        bootstrap_platform_admin(db, "not-an-email", "Long-private-passphrase-244!")


def test_command_rolls_back_and_reports_traceback_without_sql_parameters(monkeypatch, capsys):
    secret_password = "do-not-print-this-password"
    secret_url = "postgresql://user:do-not-print-this-url@localhost/db"

    class FailingSession:
        rolled_back = False
        closed = False

        def rollback(self):
            self.rolled_back = True

        def close(self):
            self.closed = True

    session = FailingSession()
    monkeypatch.setenv("PLATFORM_ADMIN_EMAIL", "bootstrap@example.test")
    monkeypatch.setenv("PLATFORM_ADMIN_PASSWORD", secret_password)
    monkeypatch.setenv("DATABASE_URL", secret_url)
    monkeypatch.setattr(bootstrap_command, "SessionLocal", lambda: session)

    def fail_before_commit(_db, _email, _password):
        raise IntegrityError(
            "INSERT", {"password_hash": "bound-hash-must-not-print"}, RuntimeError("db rejected row")
        )

    monkeypatch.setattr(bootstrap_command, "bootstrap_platform_admin", fail_before_commit)

    with pytest.raises(SystemExit) as result:
        bootstrap_command.main()

    captured = capsys.readouterr()
    assert result.value.code == 1
    assert session.rolled_back is True
    assert session.closed is True
    assert "IntegrityError" in captured.err
    assert "in main" in captured.err
    assert "bound-hash-must-not-print" not in captured.err
    assert secret_password not in captured.err
    assert secret_url not in captured.err

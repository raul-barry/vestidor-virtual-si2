from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.security import create_access_token, get_current_user
from app.core.tenancy import set_catalog_context
from app.models.organizacion import Organizacion
from app.models.rol import Rol
from app.models.sesion import Sesion
from app.models.usuario import Usuario


def _user(db):
    role = Rol(nombre="ADMINISTRADOR", estado="ACTIVO")
    user = Usuario(id_organizacion=1, rol=role, nombres="Admin", apellidos="Uno", correo="admin@tenant.test",
                   password_hash="hash", estado="ACTIVO")
    db.add(user)
    db.commit()
    return user


def _token(db, user):
    expires = datetime.now(timezone.utc) + timedelta(minutes=30)
    token = create_access_token({"id_usuario": user.id_usuario, "id_organizacion": 1, "rol": "ADMINISTRADOR"})
    db.add(Sesion(id_usuario=user.id_usuario, token_jwt=token, fecha_inicio=datetime.now(timezone.utc),
                  fecha_expiracion=expires, estado="ACTIVA"))
    db.commit()
    return token


def test_authenticated_user_establishes_database_tenant_context(db):
    user = _user(db)
    token = _token(db, user)

    authenticated = get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token), db)

    assert authenticated.id_usuario == user.id_usuario
    assert db.info["organization_id"] == 1


def test_token_cannot_select_another_organization(db):
    user = _user(db)
    db.add(Organizacion(id_organizacion=2, nombre="UrbanVogue", slug="urbanvogue", estado="ACTIVA"))
    db.commit()
    token = create_access_token({"id_usuario": user.id_usuario, "id_organizacion": 2, "rol": "ADMINISTRADOR"})

    with pytest.raises(HTTPException) as error:
        get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token), db)
    assert error.value.status_code == 401


def test_suspended_organization_invalidates_active_session(db):
    user = _user(db)
    token = _token(db, user)
    organization = db.get(Organizacion, 1)
    organization.estado = "INACTIVA"
    db.commit()

    with pytest.raises(HTTPException) as error:
        get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token), db)
    assert error.value.status_code == 403


def test_authenticated_catalog_cannot_switch_organization_using_slug(db):
    user = _user(db)
    db.add(Organizacion(id_organizacion=2, nombre="UrbanVogue", slug="urbanvogue", estado="ACTIVA"))
    db.commit()
    with pytest.raises(HTTPException) as error:
        set_catalog_context(db, "urbanvogue", user)
    assert error.value.status_code == 403

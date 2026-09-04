from app.models.rol import Rol
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.usuario import UsuarioCreate
from app.services.auth_service import AuthService


def test_creates_user_with_hashed_password(db) -> None:
    role = Rol(nombre="cliente", descripcion="Rol de cliente")
    db.add(role)
    db.flush()

    service = AuthService(db)
    usuario = service.register_usuario(
        UsuarioCreate(
            nombres="Nombre",
            apellidos="Apellido",
            correo="cliente@example.com",
            telefono="70000000",
            password="secure-password",
        ),
        id_rol=role.id_rol,
    )

    assert usuario.id_usuario is not None
    assert usuario.password_hash != "secure-password"
    assert service.verify_user_password(usuario, "secure-password")


def test_finds_user_by_email(db) -> None:
    role = Rol(nombre="administrador", descripcion=None)
    db.add(role)
    db.flush()
    service = AuthService(db)
    created = service.register_usuario(
        UsuarioCreate(
            nombres="Nombre",
            apellidos="Apellido",
            correo="admin@example.com",
            telefono=None,
            password="secure-password",
        ),
        id_rol=role.id_rol,
    )

    found = UsuarioRepository(db).get_by_correo("admin@example.com")

    assert found is not None
    assert found.id_usuario == created.id_usuario


def test_user_belongs_to_role(db) -> None:
    role = Rol(nombre="vendedor", descripcion=None)
    db.add(role)
    db.flush()
    usuario = AuthService(db).register_usuario(
        UsuarioCreate(
            nombres="Nombre",
            apellidos="Apellido",
            correo="vendedor@example.com",
            telefono=None,
            password="secure-password",
        ),
        id_rol=role.id_rol,
    )

    assert usuario.rol.nombre == "vendedor"
    assert role.usuarios == [usuario]

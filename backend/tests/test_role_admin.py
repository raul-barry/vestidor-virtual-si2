from fastapi.testclient import TestClient
from conftest import session_token
from app.main import app
from app.models.rol import Permiso, Rol
from app.models.usuario import Usuario

def headers(db):
    role=Rol(nombre="ADMINISTRADOR",descripcion="Base")
    db.add(role);db.flush()
    user=Usuario(id_rol=role.id_rol,nombres="Admin",apellidos="Test",correo="roles@example.com",password_hash="hash",estado="ACTIVO")
    db.add(user);db.commit()
    token=session_token(db,{"id_usuario":user.id_usuario,"rol":"ADMINISTRADOR"})
    return {"Authorization":f"Bearer {token}"}

def test_custom_role_permissions_and_base_protection(db):
    client=TestClient(app); auth=headers(db)
    db.add(Permiso(codigo="CATALOGO_GESTIONAR",descripcion="Catálogo"));db.commit()
    permissions=client.get("/api/admin/roles/permissions",headers=auth).json()
    assert permissions
    created=client.post("/api/admin/roles",headers=auth,json={"nombre":"EDITOR","descripcion":"Editor","permisos":[permissions[0]["id_permiso"]]})
    assert created.status_code==201
    assert created.json()["permisos"][0]["codigo"]==permissions[0]["codigo"]
    toggled=client.patch(f'/api/admin/roles/{created.json()["id_rol"]}/toggle-status',headers=auth)
    assert toggled.status_code==200 and toggled.json()["estado"]=="INACTIVO"
    restored=client.patch(f'/api/admin/roles/{created.json()["id_rol"]}/toggle-status',headers=auth)
    assert restored.status_code==200 and restored.json()["estado"]=="ACTIVO"
    edited=client.put(f'/api/admin/roles/{created.json()["id_rol"]}',headers=auth,json={"nombre":"EDITOR","descripcion":"Sin permisos","permisos":[]})
    assert edited.status_code==200 and edited.json()["permisos"]==[]
    base=next(role for role in client.get("/api/admin/roles",headers=auth).json() if role["nombre"]=="ADMINISTRADOR")
    assert client.patch(f'/api/admin/roles/{base["id_rol"]}/toggle-status',headers=auth).status_code==422
    base_updated=client.put(f'/api/admin/roles/{base["id_rol"]}',headers=auth,json={"nombre":"ADMINISTRADOR","descripcion":"Rol base protegido","permisos":[permissions[0]["id_permiso"]]})
    assert base_updated.status_code==200 and base_updated.json()["permisos"]
    assert client.put(f'/api/admin/roles/{base["id_rol"]}',headers=auth,json={"nombre":"SUPERADMIN","descripcion":"No permitido","permisos":[]}).status_code==422

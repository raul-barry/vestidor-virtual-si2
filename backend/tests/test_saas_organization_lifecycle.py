from sqlalchemy import select
from fastapi.testclient import TestClient

from conftest import session_token
from app.main import app
from app.database.plan_seed import seed_commercial_plans
from app.models.organizacion import Organizacion
from app.models.plan import Plan
from app.models.rol import Rol
from app.models.usuario import Usuario


def _headers(db, organization_id: int, role_name: str = "ADMINISTRADOR") -> dict[str, str]:
    role = db.scalar(select(Rol).where(Rol.nombre == role_name))
    if role is None:
        role = Rol(nombre=role_name, estado="ACTIVO")
        db.add(role)
        db.flush()
    user = Usuario(
        id_organizacion=None if role_name == "ADMINISTRADOR_PLATAFORMA" else organization_id,
        id_rol=role.id_rol,
        nombres="Admin",
        apellidos="Empresa" if role_name == "ADMINISTRADOR" else "Plataforma",
        correo=f"saas-{role_name.lower()}-{organization_id}@example.test",
        password_hash="not-used-in-this-test",
        estado="ACTIVO",
    )
    db.add(user)
    db.commit()
    token = session_token(db, {"id_usuario": user.id_usuario, "rol": role_name})
    return {"Authorization": f"Bearer {token}"}


def test_subscription_lifecycle_is_isolated_for_three_organizations(db):
    db.info.pop("organization_id", None)
    db.add_all([
        Organizacion(id_organizacion=2, nombre="UrbanVogue", slug="urban-vogue", estado="ACTIVA"),
        Organizacion(id_organizacion=3, nombre="Elegance Boutique", slug="elegance-boutique", estado="ACTIVA"),
    ])
    seed_commercial_plans(db)
    db.commit()
    plans = {plan.codigo: plan for plan in db.scalars(select(Plan)).all()}
    organizations = (
        (1, "ESTILO", "MODA"),
        (2, "MODA", "GLAMOUR"),
        (3, "GLAMOUR", "ESTILO"),
    )
    headers = {organization_id: _headers(db, organization_id) for organization_id, _, _ in organizations}
    platform = _headers(db, 1, "ADMINISTRADOR_PLATAFORMA")
    client = TestClient(app)

    for organization_id, assigned_code, replacement_code in organizations:
        assigned = client.post(
            f"/api/platform/organizations/{organization_id}/subscriptions",
            headers=platform,
            json={"plan_id": plans[assigned_code].id_plan},
        )
        assert assigned.status_code == 201, assigned.text
        assert assigned.json()["organizacion_id"] == organization_id
        assert assigned.json()["plan_codigo"] == assigned_code

        current = client.get("/api/subscriptions/current", headers=headers[organization_id])
        assert current.status_code == 200
        assert current.json()["organizacion_id"] == organization_id
        assert current.json()["plan_codigo"] == assigned_code

        duplicate = client.post(
            f"/api/platform/organizations/{organization_id}/subscriptions",
            headers=platform,
            json={"plan_id": plans[assigned_code].id_plan},
        )
        assert duplicate.status_code == 409

        changed = client.put(
            f"/api/platform/organizations/{organization_id}/subscriptions/current",
            headers=platform,
            json={"plan_id": plans[replacement_code].id_plan},
        )
        assert changed.status_code == 200, changed.text
        assert changed.json()["plan_codigo"] == replacement_code

        history = client.get("/api/subscriptions/history", headers=headers[organization_id])
        assert history.status_code == 200
        assert {row["plan_codigo"] for row in history.json()} == {assigned_code, replacement_code}
        assert {row["estado"] for row in history.json()} == {"ACTIVA", "FINALIZADA"}

        cancelled = client.post(
            f"/api/platform/organizations/{organization_id}/subscriptions/current/cancel",
            headers=platform,
        )
        assert cancelled.status_code == 200
        cancelled_history = client.get("/api/subscriptions/history", headers=headers[organization_id])
        assert {row["estado"] for row in cancelled_history.json()} == {"CANCELADA", "FINALIZADA"}

    # Empresa administrators can see their own subscription but not global operations.
    for organization_id, _, _ in organizations:
        current = client.get("/api/subscriptions/current", headers=headers[organization_id])
        assert current.status_code == 200
        assert current.json() is None
        assert client.get(
            f"/api/platform/organizations/{organization_id}/subscriptions/history",
            headers=headers[organization_id],
        ).status_code == 403


def test_branch_limits_match_the_three_named_organizations(db):
    from app.models.sucursal import Sucursal

    db.info.pop("organization_id", None)
    db.add_all([
        Organizacion(id_organizacion=2, nombre="UrbanVogue", slug="urban-vogue", estado="ACTIVA"),
        Organizacion(id_organizacion=3, nombre="Elegance Boutique", slug="elegance-boutique", estado="ACTIVA"),
    ])
    seed_commercial_plans(db)
    db.commit()
    plans = {plan.codigo: plan for plan in db.scalars(select(Plan)).all()}
    platform = _headers(db, 1, "ADMINISTRADOR_PLATAFORMA")
    assignments = ((1, "ESTILO", 2), (2, "MODA", 10), (3, "GLAMOUR", 11))
    for organization_id, code, _ in assignments:
        response = TestClient(app).post(
            f"/api/platform/organizations/{organization_id}/subscriptions",
            headers=platform,
            json={"plan_id": plans[code].id_plan},
        )
        assert response.status_code == 201, response.text

    client = TestClient(app)
    for organization_id, code, allowed in assignments:
        headers = _headers(db, organization_id)
        responses = [
            client.post("/api/admin/branches", headers=headers,
                        json={"nombre": f"{code} {number}", "direccion": "Calle de prueba", "ciudad": "La Paz"})
            for number in range(1, allowed + 2)
        ]
        assert all(response.status_code == 201 for response in responses[:allowed]), code
        if code == "GLAMOUR":
            assert responses[allowed].status_code == 201
            assert db.query(Sucursal).filter(Sucursal.id_organizacion == organization_id, Sucursal.estado == "ACTIVA").count() == 12
        else:
            assert responses[allowed].status_code == 403
            assert responses[allowed].json()["detail"]["code"] == "PLAN_LIMIT_REACHED"
            assert db.query(Sucursal).filter(Sucursal.id_organizacion == organization_id, Sucursal.estado == "ACTIVA").count() == allowed

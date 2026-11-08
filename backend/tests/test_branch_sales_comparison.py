from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from zipfile import ZipFile

from fastapi.testclient import TestClient
from sqlalchemy import select

from conftest import session_token
from app.main import app
from app.models.organizacion import Organizacion
from app.models.pago import Pago
from app.models.payment_refund import PaymentRefund
from app.models.plan import Plan, PlanCaracteristica
from app.models.rol import Permiso, Rol
from app.models.sucursal import Sucursal
from app.models.suscripcion import Suscripcion
from app.models.pedido import Pedido
from app.models.usuario import Usuario
from app.database.seed import seed_permissions


def _user(db, role_name="ADMINISTRADOR", email="branch-admin@example.test", branch_id=None):
    role = db.scalar(select(Rol).where(Rol.nombre == role_name))
    if role is None:
        role = Rol(nombre=role_name, descripcion=None)
        db.add(role)
        db.flush()
    user = Usuario(
        id_organizacion=1, id_sucursal=branch_id, id_rol=role.id_rol,
        nombres="Branch", apellidos="Tester", correo=email,
        password_hash="test", estado="ACTIVO",
    )
    db.add(user)
    db.commit()
    token = session_token(db, {"id_usuario": user.id_usuario, "rol": role_name})
    return {"Authorization": f"Bearer {token}"}, user


def _order(db, branch_id, day, amount, *, status="CONFIRMADO", payment_status="PAGADO"):
    order = Pedido(
        id_sucursal_entrega=branch_id,
        fecha_pedido=datetime.combine(day, datetime.min.time(), timezone.utc) + timedelta(hours=12),
        estado=status, total=Decimal(str(amount)), tipo_cliente="CLIENTE_REGISTRADO",
        tipo_venta="PRESENCIAL",
    )
    db.add(order)
    db.flush()
    payment = Pago(pedido=order, metodo_pago="EFECTIVO", monto=Decimal(str(amount)), estado=payment_status)
    db.add(payment)
    db.flush()
    return order, payment


def _comparison_data(db):
    branch_a = Sucursal(id_organizacion=1, nombre="Central", direccion="Calle 1", estado="ACTIVA")
    branch_b = Sucursal(id_organizacion=1, nombre="Norte", direccion="Calle 2", estado="ACTIVA")
    branch_empty = Sucursal(id_organizacion=1, nombre="Sur", direccion="Calle 3", estado="ACTIVA")
    db.add_all([branch_a, branch_b, branch_empty])
    db.flush()
    today = datetime.now(timezone(timedelta(hours=-4))).date()
    previous = today - timedelta(days=1)
    current_order, current_payment = _order(db, branch_a.id_sucursal, today, "120.00")
    _order(db, branch_a.id_sucursal, previous, "80.00")
    _order(db, branch_a.id_sucursal, today, "100.00", status="CANCELADO")
    _order(db, branch_a.id_sucursal, today, "60.00", payment_status="PENDIENTE")
    _order(db, branch_a.id_sucursal, today, "40.00", payment_status="FALLIDO")
    _order(db, branch_b.id_sucursal, today, "90.00")
    db.add(PaymentRefund(
        organization_id=1, payment_id=current_payment.id_pago,
        order_id=current_order.id_pedido, requested_by=1,
        operation_uuid="b3bdbeb8-e92a-46b3-8d76-edcf05f84baa",
        method="EFECTIVO", amount=Decimal("20.00"), currency="BOB",
        state="DEVOLUCION_COMPLETADA", reason="Prueba de devolución completada",
    ))
    db.commit()
    return branch_a, branch_b, branch_empty, today


def test_comparison_calculates_net_income_ticket_ranking_and_previous_period(db):
    headers, _ = _user(db)
    branch_a, branch_b, branch_empty, today = _comparison_data(db)
    response = TestClient(app).get(
        f"/api/admin/reports/comparison?fecha_inicio={today}&fecha_fin={today}",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    rows = {row["id_sucursal"]: row for row in data["sucursales"]}
    assert rows[branch_a.id_sucursal]["ingresos_netos"] == "100.00"
    assert rows[branch_a.id_sucursal]["cantidad_ventas"] == 1
    assert rows[branch_a.id_sucursal]["ticket_promedio"] == "100.00"
    assert rows[branch_a.id_sucursal]["variacion_porcentual"] == "25.00"
    assert rows[branch_b.id_sucursal]["ingresos_netos"] == "90.00"
    assert rows[branch_empty.id_sucursal]["cantidad_ventas"] == 0
    assert rows[branch_empty.id_sucursal]["variacion_porcentual"] is None
    assert data["destacados"]["mayores_ingresos"] == branch_a.id_sucursal
    assert data["destacados"]["menores_ingresos"] == branch_empty.id_sucursal


def test_comparison_filters_selected_branches_and_rejects_other_tenant(db):
    headers, _ = _user(db)
    branch_a, branch_b, _, today = _comparison_data(db)
    db.info.pop("organization_id", None)
    other = Organizacion(id_organizacion=2, nombre="Other Co", slug="other-co", estado="ACTIVA")
    db.add(other)
    db.flush()
    foreign_branch = Sucursal(id_organizacion=2, nombre="Foreign", direccion="Elsewhere", estado="ACTIVA")
    db.add(foreign_branch)
    db.commit()
    response = TestClient(app).get(
        f"/api/admin/reports/comparison?fecha_inicio={today}&fecha_fin={today}&id_sucursal={branch_b.id_sucursal}",
        headers=headers,
    )
    assert response.status_code == 200
    assert [row["id_sucursal"] for row in response.json()["sucursales"]] == [branch_b.id_sucursal]
    foreign = TestClient(app).get(
        f"/api/admin/reports/comparison?fecha_inicio={today}&fecha_fin={today}&id_sucursal={foreign_branch.id_sucursal}",
        headers=headers,
    )
    assert foreign.status_code == 404


def test_manager_permission_is_limited_to_assigned_branch_and_cashier_is_denied(db):
    _user(db, email="report-audit-actor@example.test")
    branch_a, branch_b, _, today = _comparison_data(db)
    permission = Permiso(codigo="REPORTES_COMPARATIVOS", descripcion="Branch report access")
    manager_role = Rol(nombre="ENCARGADO_SUCURSAL", descripcion=None, permisos=[permission])
    db.add(manager_role)
    db.flush()
    manager = Usuario(
        id_organizacion=1, id_sucursal=branch_a.id_sucursal, id_rol=manager_role.id_rol,
        nombres="Branch", apellidos="Manager", correo="branch-manager@example.test",
        password_hash="test", estado="ACTIVO",
    )
    cashier_role = Rol(nombre="CAJERO", descripcion=None)
    db.add_all([manager, cashier_role])
    db.flush()
    cashier = Usuario(
        id_organizacion=1, id_sucursal=branch_a.id_sucursal, id_rol=cashier_role.id_rol,
        nombres="Cash", apellidos="User", correo="cashier@example.test",
        password_hash="test", estado="ACTIVO",
    )
    db.add(cashier)
    db.commit()
    manager_headers = {"Authorization": f"Bearer {session_token(db, {'id_usuario': manager.id_usuario, 'rol': manager_role.nombre})}"}
    cashier_headers = {"Authorization": f"Bearer {session_token(db, {'id_usuario': cashier.id_usuario, 'rol': cashier_role.nombre})}"}
    client = TestClient(app)
    allowed = client.get(f"/api/admin/reports/comparison?fecha_inicio={today}&fecha_fin={today}", headers=manager_headers)
    assert allowed.status_code == 200
    assert [row["id_sucursal"] for row in allowed.json()["sucursales"]] == [branch_a.id_sucursal]
    denied_branch = client.get(
        f"/api/admin/reports/comparison?fecha_inicio={today}&fecha_fin={today}&id_sucursal={branch_b.id_sucursal}",
        headers=manager_headers,
    )
    assert denied_branch.status_code == 403
    denied_cashier = client.get("/api/admin/reports/comparison", headers=cashier_headers)
    assert denied_cashier.status_code == 403


def test_comparison_exports_pdf_and_excel_with_tenant_and_period_metadata(db):
    headers, _ = _user(db)
    _, _, _, today = _comparison_data(db)
    client = TestClient(app)
    pdf = client.get(f"/api/admin/reports/comparison/export/pdf?fecha_inicio={today}&fecha_fin={today}", headers=headers)
    xlsx = client.get(f"/api/admin/reports/comparison/export/xlsx?fecha_inicio={today}&fecha_fin={today}", headers=headers)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert "FashionStore".encode("cp1252").hex().upper().encode() in pdf.content
    assert "190.00".encode("cp1252").hex().upper().encode() in pdf.content
    assert xlsx.status_code == 200
    with ZipFile(BytesIO(xlsx.content)) as archive:
        sheet = archive.read("xl/worksheets/sheet1.xml")
    assert b"FashionStore" in sheet
    assert str(today).encode() in sheet
    assert b"190.00" in sheet


def test_comparison_requires_subscription_feature_when_subscription_exists(db):
    headers, user = _user(db)
    branch = Sucursal(id_organizacion=1, nombre="Central", direccion="Calle 1", estado="ACTIVA")
    db.add(branch)
    plan = Plan(codigo="NO_COMPARISON", nombre="No comparison", max_sucursales=2)
    db.add(plan)
    db.flush()
    db.add(PlanCaracteristica(plan_id=plan.id_plan, codigo="comparacion_sucursales", nombre="Comparison", habilitada=False))
    db.add(Suscripcion(organizacion_id=1, plan_id=plan.id_plan, estado="ACTIVA",
        fecha_inicio=datetime.now(timezone.utc) - timedelta(minutes=1)))
    db.commit()
    response = TestClient(app).get("/api/admin/reports/comparison", headers=headers)
    assert response.status_code == 403


def test_period_without_sales_returns_zero_and_no_comparison_base(db):
    headers, _ = _user(db)
    branch_a, _, _, today = _comparison_data(db)
    empty_period = today - timedelta(days=20)
    response = TestClient(app).get(
        f"/api/admin/reports/comparison?fecha_inicio={empty_period}&fecha_fin={empty_period}",
        headers=headers,
    )
    assert response.status_code == 200
    row = next(row for row in response.json()["sucursales"] if row["id_sucursal"] == branch_a.id_sucursal)
    assert Decimal(row["ingresos_netos"]) == Decimal("0.00")
    assert row["cantidad_ventas"] == 0
    assert row["variacion_porcentual"] is None


def test_platform_administrator_cannot_read_tenant_branch_sales(db):
    role = Rol(nombre="ADMINISTRADOR_PLATAFORMA", descripcion=None)
    db.add(role)
    db.flush()
    user = Usuario(
        id_organizacion=None, id_rol=role.id_rol, nombres="Platform", apellidos="Admin",
        correo="platform-report@example.test", password_hash="test", estado="ACTIVO",
    )
    db.add(user)
    db.commit()
    token = session_token(db, {"id_usuario": user.id_usuario, "rol": role.nombre})
    response = TestClient(app).get(
        "/api/admin/reports/comparison", headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in (401, 403), response.text


def test_branch_comparison_permission_seed_is_idempotent(db):
    assert seed_permissions(db) == 1
    db.commit()
    permission = db.scalar(select(Permiso).where(Permiso.codigo == "REPORTES_COMPARATIVOS"))
    assert permission is not None
    assert seed_permissions(db) == 0
"""CP-CU13: tenant branch-sales comparison API, scope, metrics and exports."""

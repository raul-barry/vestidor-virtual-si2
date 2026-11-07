from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from zipfile import ZipFile

from fastapi.testclient import TestClient
from sqlalchemy import select

from conftest import session_token
from app.core.tenancy import set_organization_context
from app.main import app
from app.models.audit_log import AuditLog
from app.models.categoria import Categoria
from app.models.organizacion import Organizacion
from app.models.plan import Plan
from app.models.producto import Producto
from app.models.rol import Rol
from app.models.sucursal import Sucursal
from app.models.suscripcion import Suscripcion
from app.models.usuario import Usuario
from test_report_admin import create_headers, create_report_data


def test_excel_export_contains_filtered_metrics_and_is_tenant_scoped(db) -> None:
    headers, admin = create_headers(db, "ADMINISTRADOR", "export-admin@example.com")
    create_report_data(db, admin)
    db.info.pop("organization_id", None)
    db.add(Organizacion(id_organizacion=2, nombre="Other Org", slug="other-org", estado="ACTIVA"))
    db.commit()
    set_organization_context(db, 2)
    db.add(Producto(
        categoria=Categoria(nombre="Other Category", descripcion=None),
        nombre="OTHER TENANT SECRET PRODUCT", descripcion=None,
        precio_base=Decimal("999"), id_organizacion=2,
    ))
    db.commit()
    set_organization_context(db, admin.id_organizacion)

    response = TestClient(app).post("/api/admin/reports/export/xlsx", headers=headers, json={
        "tipo": "productos",
        "fecha_inicio": date.today().isoformat(),
        "fecha_fin": date.today().isoformat(),
        "consulta": "",
    })

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert response.headers["cache-control"] == "no-store"
    with ZipFile(BytesIO(response.content)) as workbook:
        assert "xl/worksheets/sheet1.xml" in workbook.namelist()
        sheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "Camisa Oxford" in sheet
    assert "<v>500.00</v>" in sheet
    assert "Total unidades vendidas" in sheet
    assert "Total ingresos de productos" in sheet
    assert "OTHER TENANT SECRET PRODUCT" not in sheet
    audit = db.scalar(select(AuditLog).where(
        AuditLog.organizacion_id == admin.id_organizacion,
        AuditLog.accion == "REPORTE_EXPORTADO",
    ))
    assert audit is not None
    assert audit.detalles["formato"] == "xlsx"


def test_pdf_export_contains_report_header_and_date_filter(db) -> None:
    headers, admin = create_headers(db, "ADMINISTRADOR", "pdf-admin@example.com")
    create_report_data(db, admin)
    future = (date.today() + timedelta(days=365)).isoformat()

    response = TestClient(app).post("/api/admin/reports/export/pdf", headers=headers, json={
        "tipo": "ventas",
        "fecha_inicio": future,
        "fecha_fin": future,
        "consulta": "",
    })

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-1.4")
    assert future.encode().hex().upper().encode() in response.content
    assert b"70656469646F735F70616761646F73" in response.content  # pedidos_pagados


def test_export_rejects_branch_from_another_organization(db) -> None:
    headers, admin = create_headers(db, "ADMINISTRADOR", "branch-export-admin@example.com")
    create_report_data(db, admin)
    db.info.pop("organization_id", None)
    db.add(Organizacion(id_organizacion=2, nombre="Other Org", slug="other-org", estado="ACTIVA"))
    db.commit()
    set_organization_context(db, 2)
    other_branch = Sucursal(
        nombre="Other Tenant Branch", direccion="Other address", id_organizacion=2,
    )
    db.add(other_branch)
    db.commit()
    other_branch_id = other_branch.id_sucursal
    set_organization_context(db, admin.id_organizacion)

    response = TestClient(app).post("/api/admin/reports/export/pdf", headers=headers, json={
        "tipo": "ventas", "id_sucursal": other_branch_id,
    })

    assert response.status_code == 404
    assert response.json()["detail"] == "Sucursal no encontrada"


def test_export_requires_commercial_plan_feature(db) -> None:
    role = db.scalar(select(Rol).where(Rol.nombre == "ADMINISTRADOR"))
    if role is None:
        role = Rol(nombre="ADMINISTRADOR", descripcion=None)
        db.add(role)
        db.flush()
    user = Usuario(
        id_rol=role.id_rol, nombres="Plan", apellidos="Admin",
        correo="export-plan@example.com", password_hash="hash", estado="ACTIVO",
    )
    plan = Plan(codigo="EXPORT_LOCKED", nombre="Export Locked", max_sucursales=2)
    db.add_all([user, plan])
    db.commit()
    db.add(Suscripcion(
        organizacion_id=user.id_organizacion, plan_id=plan.id_plan, estado="ACTIVA",
        fecha_inicio=datetime.now(timezone.utc) - timedelta(minutes=1),
    ))
    db.commit()
    token = session_token(db, {"id_usuario": user.id_usuario, "rol": role.nombre})

    response = TestClient(app).post(
        "/api/admin/reports/export/pdf",
        headers={"Authorization": f"Bearer {token}"},
        json={"tipo": "ventas", "consulta": ""},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["feature"] == "exportacion_pdf_excel"

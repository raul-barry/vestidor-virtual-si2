from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from conftest import session_token
from app.core.tenancy import set_organization_context
from app.main import app
from app.models.categoria import Categoria
from app.models.cliente import Cliente
from app.models.organizacion import Organizacion
from app.models.pago import Pago
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.plan import Plan, PlanCaracteristica
from app.models.producto import Producto
from app.models.rol import Rol
from app.models.suscripcion import Suscripcion
from app.models.sucursal import Sucursal
from app.models.usuario import Usuario
from test_report_admin import create_headers, create_report_data


def _add_historical_sales(db, days: int = 56) -> None:
    product = db.scalar(select(Producto).where(Producto.nombre == "Camisa Oxford"))
    client = db.scalar(select(Cliente))
    branch = db.scalar(select(Sucursal))
    variant = product.variantes[0]
    for offset in range(days):
        sold_on = date.today() - timedelta(days=days - offset - 1)
        quantity = (offset % 4) + 1
        order = Pedido(
            cliente=client, estado="CONFIRMADO", total=Decimal(quantity * 250),
            fecha_pedido=datetime.combine(sold_on, datetime.min.time(), tzinfo=timezone.utc),
            id_sucursal_entrega=branch.id_sucursal,
        )
        db.add(order)
        db.flush()
        db.add_all([
            Pago(pedido=order, metodo_pago="QR", monto=order.total, estado="PAGADO"),
            PedidoDetalle(pedido=order, variante=variant, cantidad=quantity,
                          precio_unitario=Decimal("250")),
        ])
    db.commit()


def test_demand_forecast_evaluation_and_historical_backtest_use_real_paid_sales(db) -> None:
    headers, admin = create_headers(db, "ADMINISTRADOR", "ml-admin@example.com")
    create_report_data(db, admin)
    _add_historical_sales(db)
    start = (date.today() - timedelta(days=55)).isoformat()
    end = date.today().isoformat()

    dashboard = TestClient(app).get(
        f"/api/admin/reports/predictive/dashboard?fecha_inicio={start}&fecha_fin={end}",
        headers=headers,
    )
    history = TestClient(app).get(
        f"/api/admin/reports/predictive/history?fecha_inicio={start}&fecha_fin={end}",
        headers=headers,
    )

    assert dashboard.status_code == 200, dashboard.text
    payload = dashboard.json()
    forecast = next(
        item for item in payload["predicciones"]
        if item["producto"] == "Camisa Oxford" and item["estado_modelo"] == "evaluado"
    )
    assert len(forecast["prediccion_7_dias"]["demanda_diaria"]) == 7
    assert forecast["evaluacion"]["mae"] is not None
    assert payload["evaluacion"]["productos_evaluados"] >= 1
    assert payload["modelo"]["version"] == "weekly-seasonal-trend-v1"
    assert history.status_code == 200, history.text
    assert history.json()["resultados"]
    assert history.json()["resultados"][0]["tipo_resultado"] == "backtest_reconstruido"


def test_prediction_marks_short_history_insufficient_and_scopes_tenant(db) -> None:
    headers, admin = create_headers(db, "ADMINISTRADOR", "ml-scope@example.com")
    create_report_data(db, admin)
    db.info.pop("organization_id", None)
    db.add(Organizacion(id_organizacion=2, nombre="Other Org", slug="other-org", estado="ACTIVA"))
    db.commit()
    set_organization_context(db, 2)
    db.add(Producto(
        categoria=Categoria(nombre="Other Category", descripcion=None),
        nombre="OTHER TENANT PRODUCT", descripcion=None, precio_base=Decimal("999"),
        id_organizacion=2,
    ))
    db.commit()
    set_organization_context(db, admin.id_organizacion)

    response = TestClient(app).get("/api/admin/reports/predictive/dashboard", headers=headers)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["productos_con_datos_insuficientes"] >= 1
    assert all(item["estado_modelo"] == "datos_insuficientes" for item in payload["predicciones"])
    assert all(item["prediccion_7_dias"] is None for item in payload["predicciones"])
    assert all(item["producto"] != "OTHER TENANT PRODUCT" for item in payload["predicciones"])


def test_kmeans_segments_paid_customers_without_exposing_identifiers(db) -> None:
    headers, admin = create_headers(db, "ADMINISTRADOR", "ml-segments@example.com")
    create_report_data(db, admin)
    role = db.scalar(select(Rol).where(Rol.nombre == "CLIENTE"))
    branch_id = db.scalar(select(Sucursal.id_sucursal))
    users = []
    for index in range(8):
        user = Usuario(
            rol=role,
            nombres=f"Customer{index}",
            apellidos="Private",
            correo=f"segment-{index}@example.com",
            password_hash="not-exported",
            estado="ACTIVO",
        )
        users.append(user)
        db.add(user)
        db.flush()
        client = Cliente(usuario=user)
        db.add(client)
        db.flush()
        purchase_count = 1 if index < 4 else 4
        price = Decimal("20") if index < 4 else Decimal("400")
        for purchase in range(purchase_count):
            order = Pedido(
                cliente=client, estado="CONFIRMADO", total=price,
                id_sucursal_entrega=branch_id,
                fecha_pedido=datetime.now(timezone.utc) - timedelta(days=2 if index >= 4 else 100),
            )
            db.add(order)
            db.flush()
            db.add(Pago(pedido=order, metodo_pago="QR", monto=price, estado="PAGADO"))
    db.commit()

    response = TestClient(app).get("/api/admin/reports/predictive/segments", headers=headers)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["estado"] == "calculado"
    assert payload["clientes_analizados"] == 9
    assert 2 <= payload["k"] <= 5
    assert sum(segment["clientes"] for segment in payload["segmentos"]) == 9
    serialized = response.text
    assert "segment-" not in serialized
    assert "Customer" not in serialized
    assert "not-exported" not in serialized


def test_predictive_plan_features_are_enforced(db) -> None:
    headers, admin = create_headers(db, "ADMINISTRADOR", "ml-plan@example.com")
    plan = Plan(codigo="ML_LIMITED_TEST", nombre="ML Limited", max_sucursales=2)
    db.add(plan)
    db.flush()
    db.add(PlanCaracteristica(
        plan_id=plan.id_plan, codigo="machine_learning",
        nombre="Machine Learning", habilitada=True,
    ))
    db.add(Suscripcion(
        organizacion_id=admin.id_organizacion, plan_id=plan.id_plan, estado="ACTIVA",
        fecha_inicio=datetime.now(timezone.utc) - timedelta(minutes=1),
    ))
    db.commit()

    features = TestClient(app).get("/api/admin/reports/predictive/features", headers=headers)
    prediction = TestClient(app).get("/api/admin/reports/predictive/dashboard", headers=headers)
    segments = TestClient(app).get("/api/admin/reports/predictive/segments", headers=headers)

    assert features.status_code == 200
    assert features.json()["machine_learning"] is True
    assert features.json()["prediccion_demanda"] is False
    assert prediction.status_code == 403
    assert prediction.json()["detail"]["feature"] == "prediccion_demanda"
    assert segments.status_code == 403
    assert segments.json()["detail"]["feature"] == "segmentacion_kmeans"

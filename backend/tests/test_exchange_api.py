from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.database.seed import seed_initial_data
from app.main import app
from app.models.exchange import ExchangeInventoryIncident, GarmentExchange, OrganizationHoliday
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario
from app.models.pago import Pago
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.sucursal import Sucursal
from app.models.usuario import Usuario
from app.services.exchange_service import business_days_open
from app.services.pricing_service import current_price
from conftest import session_token


def _headers(db, email, role):
    user = db.scalar(select(Usuario).where(Usuario.correo == email))
    token = session_token(db, {"id_usuario": user.id_usuario, "rol": role})
    return user, {"Authorization": f"Bearer {token}"}


def _setup(db):
    seed_initial_data(db)
    db.commit()
    customer, customer_headers = _headers(db, "cliente@vestidor.local", "CLIENTE")
    manager, manager_headers = _headers(db, "encargado@vestidor.local", "ENCARGADO_SUCURSAL")
    admin, admin_headers = _headers(db, "admin@vestidor.local", "ADMINISTRADOR")
    original = db.scalar(select(ProductoVariante).order_by(ProductoVariante.id_variante))
    original_inventory = db.scalar(select(Inventario).where(Inventario.id_variante == original.id_variante).order_by(Inventario.id_inventario))
    replacement = db.scalar(select(ProductoVariante).join(Producto).where(
        Producto.id_categoria == original.producto.id_categoria,
        Producto.id_producto != original.producto.id_producto,
    ).order_by(ProductoVariante.id_variante))
    replacement_inventory = db.scalar(select(Inventario).where(
        Inventario.id_variante == replacement.id_variante,
        Inventario.id_sucursal == original_inventory.id_sucursal,
    ))
    paid_price = current_price(db, original.producto)
    order = Pedido(id_cliente=customer.cliente.id_cliente, fecha_pedido=datetime.now(timezone.utc) - timedelta(days=10),
        fecha_entrega=datetime.now(timezone.utc) - timedelta(days=1), estado="ENTREGADO",
        total=paid_price)
    db.add(order)
    db.flush()
    detail = PedidoDetalle(id_pedido=order.id_pedido, id_variante=original.id_variante,
        cantidad=1, precio_unitario=paid_price)
    db.add(detail)
    db.add(Pago(id_pedido=order.id_pedido, metodo_pago="EFECTIVO", monto=paid_price, estado="PAGADO"))
    db.commit()
    return (TestClient(app), customer, customer_headers, manager, manager_headers,
            admin, admin_headers, original, original_inventory, replacement,
            replacement_inventory, order, detail)


def test_business_day_window_excludes_weekends_and_configured_holidays(db):
    seed_initial_data(db)
    today = datetime.now(timezone.utc).date()
    delivered = today - timedelta(days=16)
    before = business_days_open(db, 1, delivered, today)
    holiday = delivered + timedelta(days=1)
    while holiday.weekday() >= 5:
        holiday += timedelta(days=1)
    db.add(OrganizationHoliday(organization_id=1, holiday_date=holiday, name="Feriado de prueba"))
    db.flush()
    assert business_days_open(db, 1, delivered, today) == before - 1


def test_request_rejects_other_category_and_inspection_delivers_without_new_sale(db):
    (client, _, customer_headers, _, manager_headers, _, _, original,
     original_inventory, replacement, _, order, detail) = _setup(db)
    other_category = db.scalar(select(ProductoVariante).join(Producto).where(
        Producto.id_categoria != original.producto.id_categoria,
    ).order_by(ProductoVariante.id_variante))
    assert other_category is not None
    invalid = client.post("/api/exchanges", headers=customer_headers, json={
        "id_detalle": detail.id_detalle, "id_sucursal": original_inventory.id_sucursal,
        "id_variante_sustituta": other_category.id_variante, "motivo": "Cambio de talla",
    })
    assert invalid.status_code == 422

    request = client.post("/api/exchanges", headers=customer_headers, json={
        "id_detalle": detail.id_detalle, "id_sucursal": original_inventory.id_sucursal,
        "id_variante_sustituta": original.id_variante, "motivo": "Cambio de talla",
    })
    assert request.status_code == 201, request.text
    exchange_id = request.json()["id"]
    before = original_inventory.stock_disponible
    inspection = client.post(f"/api/admin/exchanges/{exchange_id}/inspection", headers=manager_headers, json={
        "aprobado": True, "buen_estado": True, "etiqueta_original": True,
        "id_variante_sustituta": original.id_variante,
        "id_sucursal_sustituta": original_inventory.id_sucursal,
    })
    assert inspection.status_code == 200, inspection.text
    assert inspection.json()["state"] == "APROBADO"
    db.refresh(original_inventory)
    assert original_inventory.stock_disponible == before + 1
    delivered = client.post(f"/api/admin/exchanges/{exchange_id}/deliver", headers=manager_headers, json={})
    assert delivered.status_code == 200, delivered.text
    assert delivered.json()["state"] == "COMPLETADO"
    db.refresh(original_inventory)
    assert original_inventory.stock_disponible == before
    assert db.scalar(select(func.count()).select_from(Pedido)) == 1
    assert db.scalar(select(func.count()).select_from(MovimientoInventario).where(
        MovimientoInventario.motivo.like(f"%cambio {exchange_id}%"))) == 2


def test_offline_physical_shortage_is_idempotent_and_never_makes_stock_negative(db):
    (client, customer, _, manager, manager_headers, _, _, original,
     original_inventory, replacement, replacement_inventory, order, detail) = _setup(db)
    replacement_inventory.stock_disponible = 0
    original_before = original_inventory.stock_disponible
    db.commit()
    operation_uuid = str(uuid4())
    operation = {
        "operation_uuid": operation_uuid, "operation_type": "cambio.registrar_offline",
        "payload": {"id_usuario": manager.id_usuario, "id_detalle": detail.id_detalle,
            "id_sucursal": original_inventory.id_sucursal,
            "id_variante_sustituta": replacement.id_variante,
            "prenda_recibida": True, "prenda_entregada": True,
            "buen_estado": True, "etiqueta_original": True, "motivo": "Cambio físico offline"},
        "created_at": datetime.now(timezone.utc).isoformat(), "schema_version": 1,
        "client_id": "staff-device", "tenant_scope": f"org:{manager.id_organizacion}",
    }
    first = client.post("/api/sync/batch", headers=manager_headers, json={"operations": [operation]})
    replay = client.post("/api/sync/batch", headers=manager_headers, json={"operations": [operation]})
    assert first.status_code == replay.status_code == 200
    result = first.json()["results"][0]
    assert result["status"] == "SINCRONIZADA"
    assert result["result"]["state"] == "INCIDENCIA_CONCILIACION"
    assert replay.json()["results"][0]["duplicate"] is True
    db.refresh(original_inventory)
    db.refresh(replacement_inventory)
    assert original_inventory.stock_disponible == original_before + 1
    assert replacement_inventory.stock_disponible == 0
    assert db.scalar(select(func.count()).select_from(ExchangeInventoryIncident)) == 1
    assert db.scalar(select(func.count()).select_from(GarmentExchange)) == 1

    incidents = client.get("/api/admin/exchanges/incidents", headers=manager_headers)
    assert incidents.status_code == 200 and incidents.json()[0]["direction"] == "SALIDA_FISICA"
    reconcile = client.post(f"/api/admin/exchanges/incidents/{incidents.json()[0]['id']}/reconcile",
        headers=_headers(db, "admin@vestidor.local", "ADMINISTRADOR")[1],
        json={"stock_real": 0, "motivo": "Conteo físico confirmó cero"})
    assert reconcile.status_code == 200, reconcile.text
    assert reconcile.json()["state"] == "CONCILIADA"


def test_positive_difference_cannot_be_delivered_without_real_payment_confirmation(db):
    (client, _, customer_headers, _, manager_headers, _, _, original,
     original_inventory, _, _, order, detail) = _setup(db)
    detail.precio_unitario = Decimal("1.00")
    order.total = Decimal("1.00")
    db.scalar(select(Pago).where(Pago.id_pedido == order.id_pedido)).monto = Decimal("1.00")
    db.commit()
    request = client.post("/api/exchanges", headers=customer_headers, json={
        "id_detalle": detail.id_detalle, "id_sucursal": original_inventory.id_sucursal,
        "id_variante_sustituta": original.id_variante, "motivo": "Cambio de talla",
    })
    assert request.status_code == 201
    exchange_id = request.json()["id"]
    inspection = client.post(f"/api/admin/exchanges/{exchange_id}/inspection", headers=manager_headers, json={
        "aprobado": True, "buen_estado": True, "etiqueta_original": True,
        "id_variante_sustituta": original.id_variante,
    })
    assert inspection.status_code == 200
    assert inspection.json()["state"] == "PENDIENTE_COBRO"
    assert Decimal(inspection.json()["economic_difference"]) > 0
    blocked_delivery = client.post(f"/api/admin/exchanges/{exchange_id}/deliver", headers=manager_headers, json={})
    assert blocked_delivery.status_code == 409


def test_cheaper_replacement_records_refund_pending_and_does_not_fake_completion(db):
    (client, _, customer_headers, _, manager_headers, _, _, original,
     original_inventory, replacement, _, order, detail) = _setup(db)
    detail.precio_unitario = Decimal("500.00")
    order.total = Decimal("500.00")
    db.scalar(select(Pago).where(Pago.id_pedido == order.id_pedido)).monto = Decimal("500.00")
    db.commit()
    request = client.post("/api/exchanges", headers=customer_headers, json={
        "id_detalle": detail.id_detalle, "id_sucursal": original_inventory.id_sucursal,
        "id_variante_sustituta": replacement.id_variante, "motivo": "Prefiere otro modelo",
    })
    assert request.status_code == 201
    exchange_id = request.json()["id"]
    inspection = client.post(f"/api/admin/exchanges/{exchange_id}/inspection", headers=manager_headers, json={
        "aprobado": True, "buen_estado": True, "etiqueta_original": True,
        "id_variante_sustituta": replacement.id_variante,
    })
    assert inspection.status_code == 200
    assert Decimal(inspection.json()["economic_difference"]) < 0
    assert inspection.json()["financial_state"] == "PENDIENTE_DEVOLUCION"
    delivered = client.post(f"/api/admin/exchanges/{exchange_id}/deliver", headers=manager_headers, json={})
    assert delivered.status_code == 200
    assert delivered.json()["state"] == "PENDIENTE_DEVOLUCION"
    assert delivered.json()["state"] != "COMPLETADO"


def test_cu29_refund_is_server_priced_idempotent_and_requires_transfer_evidence(db):
    from app.models.payment_refund import PaymentRefund

    (client, _, customer_headers, _, manager_headers, _, admin_headers, original,
     original_inventory, replacement, _, order, detail) = _setup(db)
    detail.precio_unitario = Decimal("500.00")
    order.total = Decimal("500.00")
    payment = db.scalar(select(Pago).where(Pago.id_pedido == order.id_pedido))
    payment.monto = Decimal("500.00")
    db.commit()
    request = client.post("/api/exchanges", headers=customer_headers, json={
        "id_detalle": detail.id_detalle, "id_sucursal": original_inventory.id_sucursal,
        "id_variante_sustituta": replacement.id_variante, "motivo": "Cambio de modelo",
    })
    exchange_id = request.json()["id"]
    inspection = client.post(f"/api/admin/exchanges/{exchange_id}/inspection", headers=manager_headers, json={
        "aprobado": True, "buen_estado": True, "etiqueta_original": True,
        "id_variante_sustituta": replacement.id_variante,
    })
    assert inspection.status_code == 200
    operation_uuid = str(uuid4())
    body = {"operation_uuid": operation_uuid, "payment_id": payment.id_pago,
            "exchange_id": exchange_id, "method": "TRANSFERENCIA", "reason": "Diferencia CU29"}

    created = client.post("/api/payments/refunds", headers=admin_headers, json=body)
    replay = client.post("/api/payments/refunds", headers=admin_headers, json=body)

    assert created.status_code == replay.status_code == 201
    assert created.json()["id"] == replay.json()["id"]
    assert Decimal(created.json()["amount"]) == abs(Decimal(inspection.json()["economic_difference"]))
    assert created.json()["state"] == "DEVOLUCION_PENDIENTE"
    assert db.scalar(select(func.count()).select_from(PaymentRefund)) == 1
    completed = client.post(f"/api/payments/refunds/{created.json()['id']}/evidence",
                            headers=admin_headers, json={"evidence_reference": "TRANSFER-RECEIPT-1"})
    assert completed.status_code == 200
    assert completed.json()["state"] == "DEVOLUCION_COMPLETADA"
    assert client.post(f"/api/payments/refunds/{created.json()['id']}/evidence",
                       headers=admin_headers, json={"evidence_reference": "TRANSFER-RECEIPT-1"}).status_code == 200


def test_organization_branch_and_holiday_data_are_tenant_scoped(db):
    (client, customer, customer_headers, _, _, _, _, original,
     original_inventory, _, _, _, detail) = _setup(db)
    db.info.pop("organization_id", None)
    foreign = Sucursal(id_organizacion=2, nombre="Sucursal ajena", direccion="Otra empresa", estado="ACTIVA")
    from app.models.organizacion import Organizacion
    db.add(Organizacion(id_organizacion=2, nombre="Otra organización", slug="otra", estado="ACTIVA"))
    db.flush()
    db.add(foreign)
    db.commit()
    db.info["organization_id"] = customer.id_organizacion
    response = client.post("/api/exchanges", headers=customer_headers, json={
        "id_detalle": detail.id_detalle, "id_sucursal": foreign.id_sucursal,
        "id_variante_sustituta": original.id_variante, "motivo": "Cambio de talla",
    })
    assert response.status_code == 422
    assert client.get("/api/admin/exchanges/holidays", headers=customer_headers).status_code == 403


def _prepare_staff_exchange(db, setup):
    client, _, _, manager, manager_headers, _, _, original, original_inventory, _, _, order, detail = setup
    manager.id_sucursal = original_inventory.id_sucursal
    original_inventory.stock_vendido = 1
    replacement = db.scalar(select(ProductoVariante).where(
        ProductoVariante.id_producto == original.id_producto,
        ProductoVariante.id_variante != original.id_variante,
    ).order_by(ProductoVariante.id_variante))
    assert replacement is not None
    replacement_inventory = db.scalar(select(Inventario).where(
        Inventario.id_sucursal == original_inventory.id_sucursal,
        Inventario.id_variante == replacement.id_variante,
    ))
    if replacement_inventory is None:
        replacement_inventory = Inventario(id_sucursal=original_inventory.id_sucursal,
            id_variante=replacement.id_variante, stock_disponible=2, stock_reservado=0, stock_vendido=0)
        db.add(replacement_inventory)
    else:
        replacement_inventory.stock_disponible = 2
    db.commit()
    return client, manager_headers, order, detail, original_inventory, replacement, replacement_inventory


def test_staff_sale_lookup_and_exchange_commit_stock_history_and_idempotency(db):
    setup = _setup(db)
    client, manager_headers, order, detail, original_inventory, replacement, replacement_inventory = _prepare_staff_exchange(db, setup)
    order.id_cliente = None  # POS consumidor final: tenant is identified by its seller/branch.
    order.id_vendedor = setup[3].id_usuario
    paid_on = (datetime.now(timezone.utc) - timedelta(days=7)).date()
    db.scalar(select(Pago).where(Pago.id_pedido == order.id_pedido)).fecha_pago = datetime.combine(
        paid_on, datetime.min.time(), tzinfo=timezone.utc)
    db.commit()
    lookup = client.get(f"/api/admin/exchanges/sales/PED-{order.id_pedido}", headers=manager_headers)
    assert lookup.status_code == 200, lookup.text
    sale = lookup.json()
    assert sale["codigo"] == f"PED-{order.id_pedido}" and sale["elegible"] is True
    assert sale["detalles"][0]["cantidad_disponible_para_cambio"] == 1
    cashier = db.scalar(select(Usuario).where(Usuario.correo == "cajero@vestidor.local"))
    cashier.id_sucursal = original_inventory.id_sucursal
    db.commit()
    cashier_headers = {"Authorization": f"Bearer {session_token(db, {'id_usuario': cashier.id_usuario, 'rol': 'CAJERO'})}"}
    cashier_lookup = client.get(f"/api/admin/exchanges/sales/{order.id_pedido}", headers=cashier_headers)
    assert cashier_lookup.status_code == 200 and cashier_lookup.json()["elegible"] is True
    operation_uuid = str(uuid4())
    body = {"operation_uuid": operation_uuid, "id_detalle": detail.id_detalle,
        "id_variante_sustituta": replacement.id_variante, "cantidad": 1, "motivo": "Cambio de talla"}
    before_original = (original_inventory.stock_disponible, original_inventory.stock_vendido)
    before_replacement = (replacement_inventory.stock_disponible, replacement_inventory.stock_vendido)

    registered = client.post("/api/admin/exchanges/register", headers=manager_headers, json=body)
    replay = client.post("/api/admin/exchanges/register", headers=manager_headers, json=body)
    assert registered.status_code == replay.status_code == 201
    assert registered.json()["id"] == replay.json()["id"]
    assert registered.json()["state"] == "COMPLETADO"
    db.refresh(original_inventory)
    db.refresh(replacement_inventory)
    assert (original_inventory.stock_disponible, original_inventory.stock_vendido) == (before_original[0] + 1, before_original[1] - 1)
    assert (replacement_inventory.stock_disponible, replacement_inventory.stock_vendido) == (before_replacement[0] - 1, before_replacement[1] + 1)
    assert db.scalar(select(func.count()).select_from(MovimientoInventario).where(
        MovimientoInventario.motivo.like(f"Cambio de prenda {registered.json()['id']}:%"))) == 2
    assert client.get(f"/api/admin/exchanges/sales/{order.id_pedido}", headers=manager_headers).json()["detalles"][0]["cantidad_disponible_para_cambio"] == 0
    assert client.get("/api/admin/exchanges", headers=manager_headers).json()[0]["id"] == registered.json()["id"]


def test_staff_exchange_rejects_expired_and_unconfirmed_sales_without_stock_changes(db):
    setup = _setup(db)
    client, manager_headers, order, detail, original_inventory, replacement, replacement_inventory = _prepare_staff_exchange(db, setup)
    payment = db.scalar(select(Pago).where(Pago.id_pedido == order.id_pedido))
    before = (original_inventory.stock_disponible, original_inventory.stock_vendido,
              replacement_inventory.stock_disponible, replacement_inventory.stock_vendido)
    payment.fecha_pago = datetime.now(timezone.utc) - timedelta(days=8)
    db.commit()
    lookup = client.get(f"/api/admin/exchanges/sales/{order.id_pedido}", headers=manager_headers)
    assert lookup.status_code == 200 and lookup.json()["elegible"] is False
    assert "7 días" in lookup.json()["motivo_no_elegible"]
    body = {"operation_uuid": str(uuid4()), "id_detalle": detail.id_detalle,
        "id_variante_sustituta": replacement.id_variante, "cantidad": 1, "motivo": "Cambio de talla"}
    expired = client.post("/api/admin/exchanges/register", headers=manager_headers, json=body)
    assert expired.status_code == 422 and "venció" in expired.json()["detail"]
    payment.fecha_pago = datetime.now(timezone.utc)
    order.estado = "PENDIENTE"
    db.commit()
    unconfirmed = client.post("/api/admin/exchanges/register", headers=manager_headers,
        json={**body, "operation_uuid": str(uuid4())})
    assert unconfirmed.status_code == 422 and "no está confirmada" in unconfirmed.json()["detail"]
    db.refresh(original_inventory)
    db.refresh(replacement_inventory)
    assert (original_inventory.stock_disponible, original_inventory.stock_vendido,
            replacement_inventory.stock_disponible, replacement_inventory.stock_vendido) == before
    assert db.scalar(select(func.count()).select_from(GarmentExchange)) == 0


def test_staff_exchange_rejects_insufficient_stock_and_foreign_sale_lookup(db):
    setup = _setup(db)
    client, manager_headers, order, detail, original_inventory, replacement, replacement_inventory = _prepare_staff_exchange(db, setup)
    replacement_inventory.stock_disponible = 0
    db.commit()
    before = (original_inventory.stock_disponible, original_inventory.stock_vendido)
    body = {"operation_uuid": str(uuid4()), "id_detalle": detail.id_detalle,
        "id_variante_sustituta": replacement.id_variante, "cantidad": 1, "motivo": "Cambio de talla"}
    response = client.post("/api/admin/exchanges/register", headers=manager_headers, json=body)
    assert response.status_code == 409 and "stock suficiente" in response.json()["detail"]
    db.refresh(original_inventory)
    assert (original_inventory.stock_disponible, original_inventory.stock_vendido) == before
    assert client.get("/api/admin/exchanges/sales/999999", headers=manager_headers).status_code == 404
    assert client.get(f"/api/admin/exchanges/sales/{order.id_pedido}", headers=setup[2]).status_code == 403

    from app.models.organizacion import Organizacion
    from app.models.sucursal import Sucursal

    db.info.pop("organization_id", None)
    foreign_org = Organizacion(nombre="Empresa privada CU7", slug="cu7-privada", estado="ACTIVA")
    db.add(foreign_org)
    db.flush()
    foreign_branch = Sucursal(id_organizacion=foreign_org.id_organizacion, nombre="Sucursal CU7 privada",
        direccion="Prueba aislada", estado="ACTIVA")
    db.add(foreign_branch)
    db.flush()
    foreign_product = Producto(id_organizacion=foreign_org.id_organizacion,
        id_categoria=original_inventory.variante.producto.id_categoria,
        nombre="Producto privado CU7", precio_base=Decimal("100.00"), estado="ACTIVO")
    db.add(foreign_product)
    db.flush()
    foreign_variant = ProductoVariante(id_producto=foreign_product.id_producto,
        id_talla=original_inventory.variante.id_talla, id_color=original_inventory.variante.id_color,
        sku=f"CU7-PRIVATE-{uuid4()}", estado="ACTIVO")
    db.add(foreign_variant)
    db.flush()
    foreign_order = Pedido(id_sucursal_entrega=foreign_branch.id_sucursal, estado="ENTREGADO",
        tipo_venta="PRESENCIAL", total=Decimal("100.00"))
    db.add(foreign_order)
    db.flush()
    db.add(PedidoDetalle(id_pedido=foreign_order.id_pedido, id_variante=foreign_variant.id_variante,
        cantidad=1, precio_unitario=Decimal("100.00")))
    db.add(Pago(id_pedido=foreign_order.id_pedido, metodo_pago="EFECTIVO", monto=Decimal("100.00"), estado="PAGADO"))
    db.commit()
    foreign_sale_id = foreign_order.id_pedido
    db.info["organization_id"] = setup[3].id_organizacion
    assert client.get(f"/api/admin/exchanges/sales/{foreign_sale_id}", headers=manager_headers).status_code == 404

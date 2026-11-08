from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import get_current_admin, get_current_staff, require_roles
from app.database.database import get_db
from app.models.cliente import Cliente
from app.models.exchange import ExchangeInventoryIncident, GarmentExchange, OrganizationHoliday
from app.models.inventario import Inventario
from app.models.pago import Pago
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.sucursal import Sucursal
from app.models.usuario import Usuario
from app.services.exchange_service import (
    _branch, _purchase_context, _set_economic_state, _variant, business_days_open,
    create_customer_request, deliver_replacement, exchange_record, inspect_exchange, resolve_incident,
    register_staff_exchange, staff_sale_record,
)
from app.services.pricing_service import current_price

exchange_router = APIRouter(tags=["Cambios de prendas"])


class ExchangeRequest(BaseModel):
    id_detalle: int = Field(gt=0)
    id_sucursal: int = Field(gt=0)
    id_variante_sustituta: int | None = Field(default=None, gt=0)
    motivo: str = Field(min_length=3, max_length=255)


class InspectionRequest(BaseModel):
    aprobado: bool
    buen_estado: bool = False
    etiqueta_original: bool = False
    motivo_rechazo: str | None = Field(default=None, max_length=255)
    id_variante_sustituta: int | None = Field(default=None, gt=0)
    id_sucursal_sustituta: int | None = Field(default=None, gt=0)


class ReplacementRequest(BaseModel):
    id_variante_sustituta: int = Field(gt=0)
    id_sucursal_sustituta: int = Field(gt=0)


class StaffExchangeRequest(BaseModel):
    operation_uuid: UUID
    id_detalle: int = Field(gt=0)
    id_variante_sustituta: int = Field(gt=0)
    cantidad: int = Field(gt=0, le=1000)
    motivo: str = Field(min_length=3, max_length=255)


class HolidayRequest(BaseModel):
    fecha: date
    nombre: str = Field(min_length=2, max_length=120)


class IncidentReconcileRequest(BaseModel):
    stock_real: int = Field(ge=0)
    motivo: str = Field(min_length=3, max_length=255)


def _commit(db: Session):
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


@exchange_router.get("/exchanges/eligible")
def eligible_purchases(db: Session = Depends(get_db), user: Usuario = Depends(require_roles("CLIENTE"))):
    customer = db.scalar(select(Cliente).where(Cliente.id_usuario == user.id_usuario))
    if customer is None:
        return []
    rows = db.scalars(select(PedidoDetalle).join(Pedido).join(Pago).where(
        Pedido.id_cliente == customer.id_cliente, Pago.estado == "PAGADO",
        Pedido.estado == "ENTREGADO", Pedido.fecha_entrega.is_not(None),
    ).order_by(Pedido.fecha_entrega.desc())).all()
    result = []
    for detail in rows:
        order = detail.pedido
        delivered = order.fecha_entrega
        if delivered.tzinfo is None:
            delivered = delivered.replace(tzinfo=timezone.utc)
        if business_days_open(db, user.id_organizacion, delivered.date(), datetime.now(timezone.utc).date()) > 7:
            continue
        used = db.scalar(select(func.coalesce(func.sum(GarmentExchange.quantity), 0)).where(
            GarmentExchange.original_detail_id == detail.id_detalle,
            GarmentExchange.state != "RECHAZADO",
        )) or 0
        if used >= detail.cantidad:
            continue
        variant = detail.variante
        result.append({
            "id_detalle": detail.id_detalle, "id_pedido": order.id_pedido,
            "id_variante": variant.id_variante, "producto": variant.producto.nombre,
            "categoria": variant.producto.id_categoria, "talla": variant.talla.nombre,
            "color": variant.color.nombre, "cantidad": detail.cantidad - used,
            "precio_pagado": detail.precio_unitario, "fecha_compra": order.fecha_pedido,
            "fecha_entrega": delivered,
        })
    return result


@exchange_router.get("/exchanges/options")
def customer_exchange_options(id_detalle: int, db: Session = Depends(get_db),
                             user: Usuario = Depends(require_roles("CLIENTE"))):
    customer = db.scalar(select(Cliente).where(Cliente.id_usuario == user.id_usuario))
    if customer is None:
        raise HTTPException(403, "Cliente no registrado")
    detail, _, _, _, _, original = _purchase_context(db, user.id_organizacion, customer.id_cliente, id_detalle)
    variants = db.scalars(select(ProductoVariante).join(Producto).where(
        Producto.id_organizacion == user.id_organizacion,
        Producto.id_categoria == original.producto.id_categoria,
        Producto.estado == "ACTIVO", ProductoVariante.estado == "ACTIVO",
    ).order_by(Producto.nombre, ProductoVariante.id_variante)).all()
    branches = db.scalars(select(Sucursal).where(
        Sucursal.id_organizacion == user.id_organizacion, Sucursal.estado == "ACTIVA",
    ).order_by(Sucursal.nombre)).all()
    return {"sucursales": [{"id_sucursal": branch.id_sucursal, "nombre": branch.nombre} for branch in branches],
            "variantes": [{"id_variante": variant.id_variante, "producto": variant.producto.nombre,
                "talla": variant.talla.nombre, "color": variant.color.nombre,
                "precio": current_price(db, variant.producto),
                "stock": [{"id_sucursal": branch.id_sucursal, "sucursal": branch.nombre,
                    "disponible": db.scalar(select(Inventario.stock_disponible).where(
                        Inventario.id_sucursal == branch.id_sucursal,
                        Inventario.id_variante == variant.id_variante)) or 0} for branch in branches]}
                for variant in variants], "categoria": original.producto.id_categoria,
            "original_precio_pagado": detail.precio_unitario}


@exchange_router.post("/exchanges", status_code=201)
def request_exchange(data: ExchangeRequest, db: Session = Depends(get_db),
                     user: Usuario = Depends(require_roles("CLIENTE"))):
    customer = db.scalar(select(Cliente).where(Cliente.id_usuario == user.id_usuario))
    if customer is None:
        raise HTTPException(403, "Cliente no registrado")
    row = create_customer_request(db, organization_id=user.id_organizacion,
        customer_user_id=user.id_usuario, detail_id=data.id_detalle, branch_id=data.id_sucursal,
        replacement_variant_id=data.id_variante_sustituta, reason=data.motivo,
        operation_uuid=str(uuid4()))
    _commit(db)
    return exchange_record(db, row)


@exchange_router.get("/exchanges")
def customer_exchanges(db: Session = Depends(get_db), user: Usuario = Depends(require_roles("CLIENTE"))):
    customer = db.scalar(select(Cliente).where(Cliente.id_usuario == user.id_usuario))
    if customer is None:
        return []
    rows = db.scalars(select(GarmentExchange).where(
        GarmentExchange.customer_id == customer.id_cliente,
    ).order_by(GarmentExchange.requested_at.desc())).all()
    return [exchange_record(db, row) for row in rows]


@exchange_router.get("/admin/exchanges")
def staff_exchanges(db: Session = Depends(get_db),
                    user: Usuario = Depends(require_roles("ADMINISTRADOR", "ENCARGADO_SUCURSAL", "CAJERO"))):
    query = select(GarmentExchange)
    if user.rol.nombre == "CAJERO":
        query = query.where(GarmentExchange.branch_id == user.id_sucursal)
    rows = db.scalars(query.order_by(GarmentExchange.requested_at.desc()).limit(500)).all()
    return [exchange_record(db, row) for row in rows]


@exchange_router.get("/admin/exchanges/sales/{sale_code}")
def staff_sale_lookup(sale_code: str, db: Session = Depends(get_db),
                      user: Usuario = Depends(require_roles("ADMINISTRADOR", "ENCARGADO_SUCURSAL", "CAJERO"))):
    normalized = sale_code.strip().upper()
    if normalized.startswith("PED-"):
        normalized = normalized[4:]
    elif normalized.startswith("#"):
        normalized = normalized[1:]
    if not normalized.isdecimal() or int(normalized) < 1:
        raise HTTPException(422, "Ingresa el código de venta, por ejemplo PED-123")
    return staff_sale_record(db, sale_id=int(normalized), staff=user)


@exchange_router.post("/admin/exchanges/register", status_code=201)
def register_staff_change(data: StaffExchangeRequest, db: Session = Depends(get_db),
                          user: Usuario = Depends(require_roles("ADMINISTRADOR", "ENCARGADO_SUCURSAL", "CAJERO"))):
    try:
        row = register_staff_exchange(db, staff=user, detail_id=data.id_detalle,
            replacement_variant_id=data.id_variante_sustituta, quantity=data.cantidad,
            reason=data.motivo, operation_uuid=data.operation_uuid)
        _commit(db)
    except Exception:
        db.rollback()
        raise
    return exchange_record(db, row)


@exchange_router.get("/admin/exchanges/{exchange_id}/options")
def exchange_options(exchange_id: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_staff)):
    row = db.get(GarmentExchange, exchange_id)
    if row is None:
        raise HTTPException(404, "Cambio no encontrado")
    original = _variant(db, row.organization_id, row.original_variant_id)
    variants = db.scalars(select(ProductoVariante).join(Producto).where(
        Producto.id_organizacion == row.organization_id,
        Producto.id_categoria == original.producto.id_categoria,
        ProductoVariante.estado == "ACTIVO", Producto.estado == "ACTIVO",
    ).order_by(Producto.nombre, ProductoVariante.id_variante)).all()
    branches = db.scalars(select(Sucursal).where(Sucursal.id_organizacion == row.organization_id,
        Sucursal.estado == "ACTIVA").order_by(Sucursal.nombre)).all()
    return {"variantes": [{
        "id_variante": variant.id_variante, "producto": variant.producto.nombre,
        "talla": variant.talla.nombre, "color": variant.color.nombre,
        "categoria": variant.producto.id_categoria,
        "sucursales": [{"id_sucursal": branch.id_sucursal, "sucursal": branch.nombre,
                        "disponible": (db.scalar(select(Inventario.stock_disponible).where(
                            Inventario.id_sucursal == branch.id_sucursal,
                            Inventario.id_variante == variant.id_variante)) or 0)} for branch in branches],
    } for variant in variants], "sucursales": [{"id_sucursal": b.id_sucursal, "nombre": b.nombre} for b in branches]}


@exchange_router.post("/admin/exchanges/{exchange_id}/inspection")
def inspect(exchange_id: int, data: InspectionRequest, db: Session = Depends(get_db),
            user: Usuario = Depends(get_current_staff)):
    row = db.scalar(select(GarmentExchange).where(GarmentExchange.id == exchange_id).with_for_update())
    if row is None:
        raise HTTPException(404, "Cambio no encontrado")
    inspect_exchange(db, row, actor=user, approved=data.aprobado,
        good_condition=data.buen_estado, tag_present=data.etiqueta_original,
        rejection_reason=data.motivo_rechazo,
        replacement_variant_id=data.id_variante_sustituta,
        replacement_branch_id=data.id_sucursal_sustituta)
    _commit(db)
    return exchange_record(db, row)


@exchange_router.put("/admin/exchanges/{exchange_id}/replacement")
def choose_replacement(exchange_id: int, data: ReplacementRequest, db: Session = Depends(get_db),
                      user: Usuario = Depends(get_current_staff)):
    row = db.scalar(select(GarmentExchange).where(GarmentExchange.id == exchange_id).with_for_update())
    if row is None:
        raise HTTPException(404, "Cambio no encontrado")
    if row.inspection_state != "APROBADA" or not row.physical_original_received:
        raise HTTPException(409, "Primero debe aprobarse la inspección y recibirse la prenda")
    variant = _variant(db, row.organization_id, data.id_variante_sustituta)
    original = _variant(db, row.organization_id, row.original_variant_id)
    if variant.producto.id_categoria != original.producto.id_categoria:
        raise HTTPException(422, "El cambio debe ser de la misma categoría")
    _branch(db, row.organization_id, data.id_sucursal_sustituta)
    inventory = db.scalar(select(Inventario).where(
        Inventario.id_sucursal == data.id_sucursal_sustituta,
        Inventario.id_variante == variant.id_variante,
    ).with_for_update())
    row.replacement_variant_id = variant.id_variante
    row.replacement_branch_id = data.id_sucursal_sustituta
    row.replacement_inventory_id = inventory.id_inventario if inventory else None
    if inventory is None or inventory.stock_disponible < row.quantity:
        row.state = "PENDIENTE_DISPONIBILIDAD"
    else:
        _set_economic_state(db, row)
    _commit(db)
    return exchange_record(db, row)


@exchange_router.post("/admin/exchanges/{exchange_id}/deliver")
def deliver(exchange_id: int, db: Session = Depends(get_db), user: Usuario = Depends(get_current_staff)):
    row = db.scalar(select(GarmentExchange).where(GarmentExchange.id == exchange_id).with_for_update())
    if row is None:
        raise HTTPException(404, "Cambio no encontrado")
    result = deliver_replacement(db, row, actor=user)
    _commit(db)
    return exchange_record(db, result)


@exchange_router.get("/admin/exchanges/incidents")
def incidents(db: Session = Depends(get_db),
              user: Usuario = Depends(require_roles("ADMINISTRADOR", "ENCARGADO_SUCURSAL", "CAJERO"))):
    query = select(ExchangeInventoryIncident)
    if user.rol.nombre == "CAJERO":
        query = query.where(ExchangeInventoryIncident.branch_id == user.id_sucursal)
    rows = db.scalars(query.order_by(ExchangeInventoryIncident.created_at.desc())).all()
    return [{"id": row.id, "exchange_id": row.exchange_id, "branch_id": row.branch_id,
             "employee_id": row.employee_id, "variant_id": row.variant_id,
             "inventory_id": row.inventory_id, "direction": row.direction,
             "quantity": row.quantity, "state": row.state, "reason": row.reason,
             "created_at": row.created_at} for row in rows]


@exchange_router.post("/admin/exchanges/incidents/{incident_id}/reconcile")
def reconcile(incident_id: int, data: IncidentReconcileRequest, db: Session = Depends(get_db),
              user: Usuario = Depends(get_current_admin)):
    row = db.scalar(select(ExchangeInventoryIncident).where(
        ExchangeInventoryIncident.id == incident_id).with_for_update())
    if row is None:
        raise HTTPException(404, "Incidencia no encontrada")
    row = resolve_incident(db, row, actor=user, actual_stock=data.stock_real, reason=data.motivo)
    _commit(db)
    return {"id": row.id, "state": row.state, "resolved_at": row.resolved_at}


@exchange_router.get("/admin/exchanges/holidays")
def holidays(db: Session = Depends(get_db), user: Usuario = Depends(get_current_staff)):
    return [{"id": row.id, "fecha": row.holiday_date, "nombre": row.name}
            for row in db.scalars(select(OrganizationHoliday).where(
                OrganizationHoliday.organization_id == user.id_organizacion,
            ).order_by(OrganizationHoliday.holiday_date)).all()]


@exchange_router.post("/admin/exchanges/holidays", status_code=201)
def add_holiday(data: HolidayRequest, db: Session = Depends(get_db), user: Usuario = Depends(get_current_admin)):
    row = OrganizationHoliday(organization_id=user.id_organizacion, holiday_date=data.fecha, name=data.nombre)
    db.add(row)
    _commit(db)
    return {"id": row.id, "fecha": row.holiday_date, "nombre": row.name}


@exchange_router.delete("/admin/exchanges/holidays/{holiday_id}")
def remove_holiday(holiday_id: int, db: Session = Depends(get_db), user: Usuario = Depends(get_current_admin)):
    row = db.scalar(select(OrganizationHoliday).where(OrganizationHoliday.id == holiday_id).with_for_update())
    if row is None:
        raise HTTPException(404, "Feriado no encontrado")
    db.delete(row)
    _commit(db)
    return {"removed": True}

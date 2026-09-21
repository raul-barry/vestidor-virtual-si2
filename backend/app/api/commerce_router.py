from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from app.core.security import get_current_admin, require_roles, require_branch
from app.database.database import get_db
from app.models.comercio import Ciudad, Proveedor, Coleccion, Promocion, Devolucion
from app.models.sucursal import Sucursal
from app.models.producto import Producto
from app.models.inventario import Inventario
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.pago import Pago
from app.models.cliente import Cliente
from app.models.usuario import Usuario
from app.models.bitacora import Bitacora
from app.models.movimiento_inventario import MovimientoInventario
from app.services.pricing_service import current_price

commerce_router = APIRouter(prefix="/commerce", tags=["Operaciones comerciales"])
cashier = require_roles("ADMINISTRADOR", "CAJERO")


def record(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def commit(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Registro duplicado o asociado a otros datos")


class MasterRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    detalle: str = Field(default="", max_length=255)
    estado: Literal["ACTIVO", "INACTIVO"] = "ACTIVO"


def master_model(kind):
    if kind == "cities":
        return Ciudad, "descripcion"
    if kind not in ("suppliers", "collections"):
        raise HTTPException(404, "Maestro no encontrado")
    return (Proveedor, "contacto") if kind == "suppliers" else (Coleccion, "descripcion")


@commerce_router.get("/masters/{kind}")
def masters(kind: str, db: Session = Depends(get_db), user: Usuario = Depends(get_current_admin)):
    model, _ = master_model(kind)
    return [record(row) for row in db.scalars(select(model).order_by(model.nombre)).all()]


@commerce_router.post("/masters/{kind}", status_code=201)
def create_master(kind: str, data: MasterRequest, db: Session = Depends(get_db), user: Usuario = Depends(get_current_admin)):
    model, field = master_model(kind)
    if kind == "cities" and len(data.nombre) > 100:
        raise HTTPException(422, "Ciudad de máximo 100 caracteres")
    row = model(nombre=data.nombre, estado=data.estado, **{field: data.detalle})
    db.add(row)
    db.add(Bitacora(id_usuario=user.id_usuario, accion=f"Creación {kind}: {data.nombre}"))
    commit(db)
    return record(row)


@commerce_router.put("/masters/{kind}/{item_id}")
def edit_master(kind: str, item_id: int, data: MasterRequest, db: Session = Depends(get_db), user: Usuario = Depends(get_current_admin)):
    model, field = master_model(kind)
    row = db.get(model, item_id)
    if not row:
        raise HTTPException(404, "Registro no encontrado")
    if kind == "cities":
        if len(data.nombre) > 100:
            raise HTTPException(422, "Ciudad de máximo 100 caracteres")
        for branch in db.scalars(select(Sucursal).where(Sucursal.ciudad == row.nombre)).all():
            branch.ciudad = data.nombre
    row.nombre, row.estado = data.nombre, data.estado
    setattr(row, field, data.detalle)
    db.add(Bitacora(id_usuario=user.id_usuario, accion=f"Edición {kind}: {item_id}"))
    commit(db)
    return record(row)


@commerce_router.delete("/masters/{kind}/{item_id}", status_code=204)
def delete_master(kind: str, item_id: int, db: Session = Depends(get_db), user: Usuario = Depends(get_current_admin)):
    model, _ = master_model(kind)
    row = db.get(model, item_id)
    if not row:
        raise HTTPException(404, "Registro no encontrado")
    if kind == "cities":
        used = db.scalar(select(Sucursal).where(Sucursal.ciudad == row.nombre))
    else:
        field = Producto.id_proveedor if kind == "suppliers" else Producto.id_coleccion
        used = db.scalar(select(Producto).where(field == item_id))
    if used:
        raise HTTPException(409, "Registro asociado a sucursales o productos")
    db.delete(row)
    db.add(Bitacora(id_usuario=user.id_usuario, accion=f"Eliminación {kind}: {item_id}"))
    commit(db)


class ProductLinks(BaseModel):
    id_proveedor: int | None = None
    id_coleccion: int | None = None


@commerce_router.get("/products")
def products(db: Session = Depends(get_db), user: Usuario = Depends(get_current_admin)):
    return [record(p) for p in db.scalars(select(Producto).order_by(Producto.nombre)).all()]


@commerce_router.put("/products/{product_id}/links")
def link_product(product_id: int, data: ProductLinks, db: Session = Depends(get_db), user: Usuario = Depends(get_current_admin)):
    row = db.get(Producto, product_id)
    if not row:
        raise HTTPException(404, "Producto no encontrado")
    for name, model in [("id_proveedor", Proveedor), ("id_coleccion", Coleccion)]:
        value = getattr(data, name)
        if value is not None and db.get(model, value) is None:
            raise HTTPException(404, "Proveedor o colección no encontrado")
        setattr(row, name, value)
    db.add(Bitacora(id_usuario=user.id_usuario, accion=f"Asociación comercial producto {product_id}"))
    commit(db)
    return record(row)


class PromotionRequest(BaseModel):
    id_producto: int = Field(gt=0)
    nombre: str = Field(min_length=1, max_length=150)
    descuento: Decimal = Field(gt=0, le=100)
    inicio: date
    fin: date
    estado: Literal["ACTIVO", "INACTIVO"] = "ACTIVO"

    @model_validator(mode="after")
    def valid_dates(self):
        if self.fin < self.inicio:
            raise ValueError("La fecha final debe ser posterior al inicio")
        return self


@commerce_router.get("/promotions")
def promotions(db: Session = Depends(get_db), user: Usuario = Depends(get_current_admin)):
    return [record(r) for r in db.scalars(select(Promocion).order_by(Promocion.id_promocion.desc())).all()]


@commerce_router.post("/promotions", status_code=201)
def create_promotion(data: PromotionRequest, db: Session = Depends(get_db), user: Usuario = Depends(get_current_admin)):
    if not db.get(Producto, data.id_producto):
        raise HTTPException(404, "Producto no encontrado")
    row = Promocion(**data.model_dump())
    db.add(row)
    db.add(Bitacora(id_usuario=user.id_usuario, accion=f"Promoción: {data.nombre}"))
    commit(db)
    return record(row)


@commerce_router.put("/promotions/{promotion_id}")
def edit_promotion(promotion_id: int, data: PromotionRequest, db: Session = Depends(get_db), user: Usuario = Depends(get_current_admin)):
    row = db.get(Promocion, promotion_id)
    if not row or not db.get(Producto, data.id_producto):
        raise HTTPException(404, "Promoción o producto no encontrado")
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    db.add(Bitacora(id_usuario=user.id_usuario, accion=f"Edición promoción {promotion_id}"))
    commit(db)
    return record(row)


@commerce_router.get("/pos/options")
def pos_options(db: Session = Depends(get_db), user: Usuario = Depends(cashier)):
    return {"clientes": [dict(id_cliente=c.id_cliente, nombre=f"{c.usuario.nombres} {c.usuario.apellidos}")
                          for c in db.scalars(select(Cliente)).all() if c.usuario.estado.upper() == "ACTIVO"],
            "inventario": [dict(id_inventario=i.id_inventario, id_sucursal=i.id_sucursal,
                                producto=i.variante.producto.nombre, talla=i.variante.talla.nombre,
                                color=i.variante.color.nombre, sucursal=i.sucursal.nombre,
                                stock=i.stock_disponible, precio=current_price(db, i.variante.producto))
                           for i in db.scalars(select(Inventario)).all() if i.stock_disponible > 0
                           and i.variante.estado == "ACTIVO" and i.variante.producto.estado == "ACTIVO"
                           and i.sucursal.estado == "ACTIVA"
                           and (user.rol.nombre == "ADMINISTRADOR" or i.id_sucursal == user.id_sucursal)]}


class SaleLine(BaseModel):
    id_inventario: int = Field(gt=0)
    cantidad: int = Field(gt=0, le=1000)


class SaleRequest(BaseModel):
    id_cliente: int | None = Field(default=None, gt=0)
    tipo_cliente: Literal["CLIENTE_REGISTRADO", "CONSUMIDOR_FINAL"] = "CLIENTE_REGISTRADO"
    metodo_pago: Literal["EFECTIVO", "QR", "TARJETA"]
    nit_ci: str | None = Field(default=None, max_length=30)
    razon_social: str | None = Field(default=None, max_length=150)
    tipo_entrega: Literal["RECOJO_SUCURSAL", "DELIVERY"] = "RECOJO_SUCURSAL"
    id_sucursal_entrega: int | None = Field(default=None, gt=0)
    direccion_entrega: str | None = Field(default=None, max_length=255)
    referencia_entrega: str | None = Field(default=None, max_length=255)
    telefono_entrega: str | None = Field(default=None, max_length=30)
    items: list[SaleLine] = Field(min_length=1, max_length=100)


@commerce_router.post("/pos", status_code=201)
def sale(data: SaleRequest, db: Session = Depends(get_db), user: Usuario = Depends(cashier)):
    if data.tipo_cliente == "CLIENTE_REGISTRADO":
        customer = db.get(Cliente, data.id_cliente)
        if not customer or customer.usuario.estado.upper() != "ACTIVO":
            raise HTTPException(404, "Cliente registrado no encontrado")
    elif data.id_cliente is not None:
        raise HTTPException(422, "Consumidor final no debe asociarse a un cliente registrado")
    if bool(data.nit_ci) != bool(data.razon_social):
        raise HTTPException(422, "NIT/CI y razón social deben registrarse juntos")
    if data.tipo_entrega == "DELIVERY" and (not data.direccion_entrega or not data.telefono_entrega):
        raise HTTPException(422, "Delivery requiere dirección y teléfono")
    quantities = {}
    for line in data.items:
        quantities[line.id_inventario] = quantities.get(line.id_inventario, 0) + line.cantidad
    rows = []
    for inv_id, quantity in sorted(quantities.items()):
        inv = db.scalar(select(Inventario).where(Inventario.id_inventario == inv_id).with_for_update())
        if not inv or inv.stock_disponible < quantity or inv.sucursal.estado != "ACTIVA" or inv.variante.estado != "ACTIVO" or inv.variante.producto.estado != "ACTIVO":
            raise HTTPException(409, "Stock insuficiente o prenda inactiva")
        require_branch(user, inv.id_sucursal)
        rows.append((inv, quantity, current_price(db, inv.variante.producto)))
    if len({inv.id_sucursal for inv, _, _ in rows}) != 1:
        raise HTTPException(422, "Seleccione productos de una sola sucursal")
    delivery_branch = data.id_sucursal_entrega or rows[0][0].id_sucursal
    if data.tipo_entrega == "RECOJO_SUCURSAL" and not db.get(Sucursal, delivery_branch):
        raise HTTPException(404, "Sucursal de recojo no encontrada")
    order = Pedido(
        id_vendedor=user.id_usuario,
        id_cliente=data.id_cliente, estado="ENTREGADO" if data.metodo_pago == "EFECTIVO" else "PENDIENTE",
        total=sum(price * qty for _, qty, price in rows), tipo_cliente=data.tipo_cliente,
        tipo_venta="PRESENCIAL", nit_ci=data.nit_ci, razon_social=data.razon_social,
        tipo_entrega=data.tipo_entrega, id_sucursal_entrega=delivery_branch if data.tipo_entrega == "RECOJO_SUCURSAL" else None,
        direccion_entrega=data.direccion_entrega if data.tipo_entrega == "DELIVERY" else None,
        referencia_entrega=data.referencia_entrega if data.tipo_entrega == "DELIVERY" else None,
        telefono_entrega=data.telefono_entrega if data.tipo_entrega == "DELIVERY" else None,
    )
    db.add(order)
    db.flush()
    for inv, quantity, price in rows:
        db.add(PedidoDetalle(id_pedido=order.id_pedido, id_variante=inv.id_variante, cantidad=quantity, precio_unitario=price))
        previous = inv.stock_disponible
        inv.stock_disponible -= quantity
        db.add(MovimientoInventario(id_inventario=inv.id_inventario, tipo_movimiento="SALIDA",
            cantidad=quantity, stock_anterior=previous, stock_nuevo=inv.stock_disponible,
            motivo=f"Venta presencial pedido {order.id_pedido}", id_usuario=user.id_usuario))
    db.add(Pago(id_pedido=order.id_pedido, metodo_pago=data.metodo_pago, monto=order.total, estado="PAGADO"))
    db.add(Bitacora(id_usuario=user.id_usuario, accion=f"Venta presencial pedido {order.id_pedido}"))
    commit(db)
    return record(order)


@commerce_router.get("/returns/options")
def return_options(db: Session = Depends(get_db), user: Usuario = Depends(get_current_admin)):
    rows = db.scalars(select(PedidoDetalle).join(Pedido).join(Pago).where(Pago.estado == "PAGADO")).all()
    return {"detalles": [dict(id_detalle=r.id_detalle, id_pedido=r.id_pedido, id_variante=r.id_variante,
                             producto=r.variante.producto.nombre, talla=r.variante.talla.nombre,
                             color=r.variante.color.nombre, cantidad=r.cantidad,
                             devuelto=db.scalar(select(func.coalesce(func.sum(Devolucion.cantidad), 0)).where(Devolucion.id_detalle == r.id_detalle))) for r in rows],
            "inventario": [dict(id_inventario=i.id_inventario, id_variante=i.id_variante, sucursal=i.sucursal.nombre) for i in db.scalars(select(Inventario)).all()]}


@commerce_router.get("/returns")
def returns(db: Session = Depends(get_db), user: Usuario = Depends(get_current_admin)):
    return [record(r) for r in db.scalars(select(Devolucion).order_by(Devolucion.id_devolucion.desc())).all()]


class ReturnRequest(BaseModel):
    id_detalle: int = Field(gt=0)
    id_inventario: int = Field(gt=0)
    cantidad: int = Field(gt=0, le=1000)
    motivo: str = Field(min_length=3, max_length=255)


class ReturnStatusRequest(BaseModel):
    estado: Literal["PENDIENTE", "APROBADA", "RECHAZADA", "COMPLETADA"]


@commerce_router.post("/returns", status_code=201)
def create_return(data: ReturnRequest, db: Session = Depends(get_db), user: Usuario = Depends(get_current_admin)):
    detail = db.scalar(select(PedidoDetalle).where(PedidoDetalle.id_detalle == data.id_detalle).with_for_update())
    if not detail:
        raise HTTPException(404, "Detalle no encontrado")
    payment = db.scalar(select(Pago).where(Pago.id_pedido == detail.id_pedido, Pago.estado == "PAGADO"))
    returned = db.scalar(select(func.coalesce(func.sum(Devolucion.cantidad), 0)).where(Devolucion.id_detalle == data.id_detalle))
    if not payment or returned + data.cantidad > detail.cantidad:
        raise HTTPException(409, "Cantidad excedida o venta sin pago aprobado")
    inv = db.scalar(select(Inventario).where(Inventario.id_inventario == data.id_inventario).with_for_update())
    if not inv or inv.id_variante != detail.id_variante:
        raise HTTPException(422, "Inventario incompatible con la variante vendida")
    row = Devolucion(id_usuario=user.id_usuario, **data.model_dump())
    db.add(row)
    previous = inv.stock_disponible
    inv.stock_disponible += data.cantidad
    db.add(MovimientoInventario(id_inventario=inv.id_inventario, tipo_movimiento="ENTRADA", cantidad=data.cantidad,
        stock_anterior=previous, stock_nuevo=inv.stock_disponible, motivo=f"Devolución pedido {detail.id_pedido}", id_usuario=user.id_usuario))
    db.add(Bitacora(id_usuario=user.id_usuario, accion=f"Devolución pedido {detail.id_pedido}: {data.cantidad}"))
    commit(db)
    return record(row)


@commerce_router.put("/returns/{return_id}/status")
def update_return_status(
    return_id: int,
    data: ReturnStatusRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_admin),
):
    row = db.get(Devolucion, return_id)
    if not row:
        raise HTTPException(404, "Devolución no encontrada")
    if row.estado == "COMPLETADA" and data.estado != "COMPLETADA":
        raise HTTPException(409, "La devolución ya fue completada")
    row.estado = data.estado
    db.add(Bitacora(id_usuario=user.id_usuario, accion=f"Devolución {return_id}: {data.estado}"))
    commit(db)
    return record(row)


@commerce_router.get("/audit")
def audit(db: Session = Depends(get_db), user: Usuario = Depends(get_current_admin)):
    return [
        {
            **record(row),
            "usuario": f"{row.usuario.nombres} {row.usuario.apellidos}",
            "correo": row.usuario.correo,
            "rol": row.usuario.rol.nombre,
            "resultado": "EXITOSO",
        }
        for row in db.scalars(select(Bitacora).order_by(Bitacora.nro_bitacora.desc()).limit(500)).all()
    ]


@commerce_router.get("/sales-history")
def sales_history(
    fecha_desde: date | None = None, fecha_hasta: date | None = None, id_cliente: int | None = None,
    id_vendedor: int | None = None, id_sucursal: int | None = None, metodo_pago: str | None = None,
    estado: str | None = None, tipo_venta: str | None = None,
    db: Session = Depends(get_db), user: Usuario = Depends(get_current_admin),
):
    customer_user = aliased(Usuario); seller = aliased(Usuario)
    query = (select(Pedido, Pago, Cliente, customer_user, seller, Sucursal).outerjoin(Pago, Pago.id_pedido == Pedido.id_pedido)
             .outerjoin(Cliente, Cliente.id_cliente == Pedido.id_cliente).outerjoin(customer_user, customer_user.id_usuario == Cliente.id_usuario)
             .outerjoin(seller, seller.id_usuario == Pedido.id_vendedor).outerjoin(Sucursal, Sucursal.id_sucursal == Pedido.id_sucursal_entrega)
             .order_by(Pedido.fecha_pedido.desc()))
    if fecha_desde: query = query.where(func.date(Pedido.fecha_pedido) >= fecha_desde)
    if fecha_hasta: query = query.where(func.date(Pedido.fecha_pedido) <= fecha_hasta)
    if id_cliente: query = query.where(Pedido.id_cliente == id_cliente)
    if id_vendedor: query = query.where(Pedido.id_vendedor == id_vendedor)
    if id_sucursal: query = query.where(Pedido.id_sucursal_entrega == id_sucursal)
    if metodo_pago: query = query.where(Pago.metodo_pago == metodo_pago)
    if estado: query = query.where(Pedido.estado == estado)
    if tipo_venta: query = query.where(Pedido.tipo_venta == tipo_venta)
    return [dict(id_pedido=p.id_pedido, fecha=p.fecha_pedido, cliente=(f"{cu.nombres} {cu.apellidos}" if cu else "Consumidor final"), tipo_cliente=p.tipo_cliente, vendedor=(f"{su.nombres} {su.apellidos}" if su else "—"), sucursal=(branch.nombre if branch else "—"), metodo_pago=(pay.metodo_pago if pay else "PENDIENTE"), total=p.total, estado=p.estado, tipo_venta=p.tipo_venta) for p,pay,_,cu,su,branch in db.execute(query).all()]

@commerce_router.get("/sales-history/options")
def sales_history_options(db: Session = Depends(get_db), user: Usuario = Depends(get_current_admin)):
    return {"clientes":[{"id":c.id_cliente,"nombre":f"{c.usuario.nombres} {c.usuario.apellidos}"} for c in db.scalars(select(Cliente)).all()],"vendedores":[{"id":u.id_usuario,"nombre":f"{u.nombres} {u.apellidos}"} for u in db.scalars(select(Usuario)).all() if u.rol.nombre in ("ADMINISTRADOR","CAJERO")],"sucursales":[{"id":s.id_sucursal,"nombre":s.nombre} for s in db.scalars(select(Sucursal)).all()]}


@commerce_router.get("/sales-history/{order_id}")
def sales_history_detail(order_id: int, db: Session = Depends(get_db), user: Usuario = Depends(get_current_admin)):
    order = db.get(Pedido, order_id)
    if not order: raise HTTPException(404, "Venta no encontrada")
    payment = db.scalar(select(Pago).where(Pago.id_pedido == order_id))
    return {"id_pedido":order.id_pedido,"total":order.total,"estado":order.estado,"tipo_entrega":order.tipo_entrega,"pago":record(payment) if payment else None,"entrega":{"sucursal": order.id_sucursal_entrega,"direccion":order.direccion_entrega,"referencia":order.referencia_entrega,"telefono":order.telefono_entrega},"detalles":[{"producto":d.variante.producto.nombre,"talla":d.variante.talla.nombre,"color":d.variante.color.nombre,"cantidad":d.cantidad,"precio_unitario":d.precio_unitario,"subtotal":d.cantidad*d.precio_unitario} for d in order.detalles]}

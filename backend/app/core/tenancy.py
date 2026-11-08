"""SQLAlchemy-level organization scoping shared by API repositories and services."""

from sqlalchemy import and_, exists, or_, select, event, inspect
from sqlalchemy.orm import Session, with_loader_criteria

from app.models import (
    Bitacora, Carrito, CarritoDetalle, Cliente, Coleccion, Devolucion, Inventario,
    MovimientoInventario, Organizacion, Pago, Pedido, PedidoDetalle, PerfilCorporal,
    Plan, PreferenciaCliente, PreferenciaClienteColor, Producto, ProductoVariante,
    Promocion, Proveedor, RecursoVirtual, Reserva, Sesion, Sucursal,
    Suscripcion, TokenRecuperacion, Usuario, AuditLog, MovimientoInventario, SyncIdempotency,
    DeviceSyncCredential, GarmentExchange, ExchangeInventoryIncident, OrganizationHoliday,
    PaymentRefund, PaymentAdjustment, LoyaltyProgram, LoyaltyAccount, LoyaltyTier, LoyaltyLedger,
)


def set_organization_context(db: Session, organization_id: int) -> None:
    db.info["organization_id"] = organization_id


def select_public_organization(db: Session, slug: str | None) -> Organizacion:
    query = select(Organizacion).where(Organizacion.estado == "ACTIVA")
    if slug:
        query = query.where(Organizacion.slug == slug)
    else:
        query = query.where(Organizacion.slug == "fashionstore")
    organization = db.scalar(query)
    if organization is None:
        from fastapi import HTTPException
        raise HTTPException(404, "Empresa no encontrada o inactiva")
    return organization


def set_catalog_context(db: Session, slug: str | None, current_user: Usuario | None) -> None:
    organization = (db.get(Organizacion, current_user.id_organizacion)
                    if current_user is not None and slug is None
                    else select_public_organization(db, slug))
    if organization is None or organization.estado.upper() != "ACTIVA":
        from fastapi import HTTPException
        raise HTTPException(404, "Empresa no encontrada o inactiva")
    if current_user is not None and current_user.id_organizacion != organization.id_organizacion:
        from fastapi import HTTPException
        raise HTTPException(403, "El catálogo solicitado no pertenece a tu empresa")
    set_organization_context(db, organization.id_organizacion)


def _user(user_id, org_id):
    t = Usuario.__table__
    return exists(select(1).select_from(t).where(t.c.id_usuario == user_id, t.c.id_organizacion == org_id).correlate_except(t))


def _client(client_id, org_id):
    c, u = Cliente.__table__, Usuario.__table__
    return exists(select(1).select_from(c.join(u, c.c.id_usuario == u.c.id_usuario)).where(
        c.c.id_cliente == client_id, u.c.id_organizacion == org_id
    ).correlate_except(c, u))


def _product(product_id, org_id):
    t = Producto.__table__
    return exists(select(1).select_from(t).where(t.c.id_producto == product_id, t.c.id_organizacion == org_id).correlate_except(t))


def _variant(variant_id, org_id):
    v, p = ProductoVariante.__table__, Producto.__table__
    return exists(select(1).select_from(v.join(p, v.c.id_producto == p.c.id_producto)).where(
        v.c.id_variante == variant_id, p.c.id_organizacion == org_id
    ).correlate_except(v, p))


def _branch(branch_id, org_id):
    t = Sucursal.__table__
    return exists(select(1).select_from(t).where(t.c.id_sucursal == branch_id, t.c.id_organizacion == org_id).correlate_except(t))


def _inventory(inventory_id, org_id):
    i, b, v, p = Inventario.__table__, Sucursal.__table__, ProductoVariante.__table__, Producto.__table__
    source = i.join(b, i.c.id_sucursal == b.c.id_sucursal).join(v, i.c.id_variante == v.c.id_variante).join(p, v.c.id_producto == p.c.id_producto)
    return exists(select(1).select_from(source).where(
        i.c.id_inventario == inventory_id, b.c.id_organizacion == org_id, p.c.id_organizacion == org_id
    ).correlate_except(i, b, v, p))


def _cart(cart_id, org_id):
    a, c, u = Carrito.__table__, Cliente.__table__, Usuario.__table__
    source = a.join(c, a.c.id_cliente == c.c.id_cliente).join(u, c.c.id_usuario == u.c.id_usuario)
    return exists(select(1).select_from(source).where(a.c.id_carrito == cart_id, u.c.id_organizacion == org_id).correlate_except(a, c, u))


def _order(order_id, org_id):
    p = Pedido.__table__
    return exists(select(1).select_from(p).where(
        p.c.id_pedido == order_id,
        or_(_client(p.c.id_cliente, org_id), _user(p.c.id_vendedor, org_id), _branch(p.c.id_sucursal_entrega, org_id)),
    ).correlate_except(p))


def install_tenant_session_hooks() -> None:
    @event.listens_for(Session, "do_orm_execute")
    def apply_organization_scope(execute_state):
        org_id = execute_state.session.info.get("organization_id")
        if org_id is None or not execute_state.is_orm_statement:
            return
        criteria = (
            (Usuario, lambda cls: cls.id_organizacion == org_id),
            (Sucursal, lambda cls: cls.id_organizacion == org_id),
            (Producto, lambda cls: cls.id_organizacion == org_id),
            (Proveedor, lambda cls: cls.id_organizacion == org_id),
            (Coleccion, lambda cls: cls.id_organizacion == org_id),
            (Cliente, lambda cls: _user(cls.id_usuario, org_id)),
            (ProductoVariante, lambda cls: _product(cls.id_producto, org_id)),
            (Inventario, lambda cls: and_(_branch(cls.id_sucursal, org_id), _variant(cls.id_variante, org_id))),
            (Carrito, lambda cls: _client(cls.id_cliente, org_id)),
            (CarritoDetalle, lambda cls: and_(_cart(cls.id_carrito, org_id), _variant(cls.id_variante, org_id))),
            (Pedido, lambda cls: or_(_client(cls.id_cliente, org_id), _user(cls.id_vendedor, org_id), _branch(cls.id_sucursal_entrega, org_id))),
            (PedidoDetalle, lambda cls: and_(_order(cls.id_pedido, org_id), _variant(cls.id_variante, org_id))),
            (Pago, lambda cls: _order(cls.id_pedido, org_id)),
            (PaymentRefund, lambda cls: cls.organization_id == org_id),
            (PaymentAdjustment, lambda cls: cls.organization_id == org_id),
            (LoyaltyProgram, lambda cls: cls.organization_id == org_id),
            (LoyaltyAccount, lambda cls: cls.organization_id == org_id),
            (LoyaltyTier, lambda cls: cls.organization_id == org_id),
            (LoyaltyLedger, lambda cls: cls.organization_id == org_id),
            (Reserva, lambda cls: and_(_user(cls.id_usuario, org_id), _inventory(cls.id_inventario, org_id), or_(cls.id_pedido.is_(None), _order(cls.id_pedido, org_id)))),
            (MovimientoInventario, lambda cls: and_(_inventory(cls.id_inventario, org_id), _user(cls.id_usuario, org_id))),
            (Devolucion, lambda cls: and_(
                exists(select(1).select_from(PedidoDetalle.__table__).where(PedidoDetalle.__table__.c.id_detalle == cls.id_detalle, _order(PedidoDetalle.__table__.c.id_pedido, org_id))),
                _inventory(cls.id_inventario, org_id), _user(cls.id_usuario, org_id),
            )),
            (Bitacora, lambda cls: _user(cls.id_usuario, org_id)),
            (Sesion, lambda cls: _user(cls.id_usuario, org_id)),
            (TokenRecuperacion, lambda cls: _user(cls.id_usuario, org_id)),
            (PerfilCorporal, lambda cls: _user(cls.id_usuario, org_id)),
            (PreferenciaCliente, lambda cls: _client(cls.id_cliente, org_id)),
            (PreferenciaClienteColor, lambda cls: exists(select(1).select_from(
                PreferenciaClienteColor.__table__.join(PreferenciaCliente.__table__, PreferenciaClienteColor.__table__.c.id_preferencia == PreferenciaCliente.__table__.c.id_preferencia)
                .join(Cliente.__table__, PreferenciaCliente.__table__.c.id_cliente == Cliente.__table__.c.id_cliente)
                .join(Usuario.__table__, Cliente.__table__.c.id_usuario == Usuario.__table__.c.id_usuario)
            ).where(PreferenciaClienteColor.__table__.c.id_preferencia == cls.id_preferencia, Usuario.__table__.c.id_organizacion == org_id))),
            (Promocion, lambda cls: _product(cls.id_producto, org_id)),
            (RecursoVirtual, lambda cls: _product(cls.id_producto, org_id)),
            (Suscripcion, lambda cls: cls.organizacion_id == org_id),
            (AuditLog, lambda cls: cls.organizacion_id == org_id),
            (SyncIdempotency, lambda cls: cls.organizacion_id == org_id),
            (DeviceSyncCredential, lambda cls: cls.organizacion_id == org_id),
            (GarmentExchange, lambda cls: cls.organization_id == org_id),
            (ExchangeInventoryIncident, lambda cls: cls.organization_id == org_id),
            (OrganizationHoliday, lambda cls: cls.organization_id == org_id),
        )
        for entity, criterion in criteria:
            execute_state.statement = execute_state.statement.options(
                with_loader_criteria(entity, criterion, include_aliases=True)
            )

    @event.listens_for(Session, "before_flush")
    def require_explicit_organization(session, _flush_context, _instances):
        org_id = session.info.get("organization_id")
        if org_id is None:
            return
        for entity in session.new.union(session.dirty).union(session.deleted):
            if isinstance(entity, (Usuario, Sucursal, Producto, Proveedor, Coleccion)):
                if entity.id_organizacion is None:
                    entity.id_organizacion = org_id
                elif entity.id_organizacion != org_id:
                    raise ValueError("La organización del registro no coincide con el usuario autenticado")
            elif isinstance(entity, Suscripcion) and entity.organizacion_id != org_id:
                raise ValueError("La suscripción no pertenece a la organización autenticada")

            elif isinstance(entity, SyncIdempotency):
                if entity.organizacion_id is None:
                    entity.organizacion_id = org_id
                elif entity.organizacion_id != org_id:
                    raise ValueError("El registro de sincronización no pertenece a la organización autenticada")

            elif isinstance(entity, DeviceSyncCredential) and entity.organizacion_id != org_id:
                raise ValueError("La credencial de sincronización no pertenece a la organización autenticada")

            elif isinstance(entity, (GarmentExchange, ExchangeInventoryIncident, OrganizationHoliday)) and entity.organization_id != org_id:
                raise ValueError("El cambio no pertenece a la organización autenticada")

        for entity in session.new.union(session.dirty).union(session.deleted):
            if isinstance(entity, (PaymentRefund, PaymentAdjustment, LoyaltyProgram, LoyaltyAccount, LoyaltyTier, LoyaltyLedger)) and entity.organization_id != org_id:
                raise ValueError("La operaciÃ³n financiera no pertenece a la organizaciÃ³n autenticada")

        def belongs(model, key, value):
            if value is None:
                return True
            row = session.get(model, value)
            return row is not None

        for entity in session.new.union(session.dirty).union(session.deleted):
            references = []
            if isinstance(entity, Usuario):
                references = [(Sucursal, "id_sucursal")]
            elif isinstance(entity, Producto):
                references = [(Proveedor, "id_proveedor"), (Coleccion, "id_coleccion")]
            elif isinstance(entity, Inventario):
                references = [(Sucursal, "id_sucursal"), (ProductoVariante, "id_variante")]
            elif isinstance(entity, Reserva):
                references = [(Usuario, "id_usuario"), (Inventario, "id_inventario"), (Pedido, "id_pedido")]
            elif isinstance(entity, Carrito):
                references = [(Cliente, "id_cliente")]
            elif isinstance(entity, CarritoDetalle):
                references = [(Carrito, "id_carrito"), (ProductoVariante, "id_variante")]
            elif isinstance(entity, Pedido):
                references = [(Cliente, "id_cliente"), (Usuario, "id_vendedor"), (Sucursal, "id_sucursal_entrega")]
            elif isinstance(entity, PedidoDetalle):
                references = [(Pedido, "id_pedido"), (ProductoVariante, "id_variante"), (Reserva, "id_reserva")]
            elif isinstance(entity, GarmentExchange):
                references = [(Cliente, "customer_id"), (Pedido, "original_order_id"),
                              (PedidoDetalle, "original_detail_id"), (ProductoVariante, "original_variant_id"),
                              (ProductoVariante, "replacement_variant_id"), (Sucursal, "branch_id"),
                              (Sucursal, "replacement_branch_id"),
                              (Inventario, "original_inventory_id"), (Inventario, "replacement_inventory_id"),
                              (Usuario, "employee_id")]
            elif isinstance(entity, ExchangeInventoryIncident):
                references = [(GarmentExchange, "exchange_id"), (Sucursal, "branch_id"),
                              (Usuario, "employee_id"), (ProductoVariante, "variant_id"),
                              (Inventario, "inventory_id"), (Usuario, "resolved_by")]
            elif isinstance(entity, Pago):
                references = [(Pedido, "id_pedido")]
            elif isinstance(entity, PaymentRefund):
                references = [(Pago, "payment_id"), (Pedido, "order_id"), (Usuario, "requested_by"),
                              (GarmentExchange, "exchange_id"), (Devolucion, "return_id")]
            elif isinstance(entity, PaymentAdjustment):
                references = [(GarmentExchange, "exchange_id"), (Pago, "original_payment_id")]
            elif isinstance(entity, LoyaltyAccount):
                references = [(Cliente, "customer_id")]
            elif isinstance(entity, LoyaltyLedger):
                references = [(LoyaltyAccount, "account_id"), (Pedido, "order_id")]
            elif isinstance(entity, MovimientoInventario):
                references = [(Inventario, "id_inventario"), (Usuario, "id_usuario")]
            elif isinstance(entity, Devolucion):
                references = [(PedidoDetalle, "id_detalle"), (Inventario, "id_inventario"), (Usuario, "id_usuario")]
            elif isinstance(entity, (Bitacora, Sesion, TokenRecuperacion, PerfilCorporal, PreferenciaCliente)):
                references = [(Usuario, "id_usuario")]
            elif isinstance(entity, RecursoVirtual):
                references = [(Producto, "id_producto")]
            elif isinstance(entity, Promocion):
                references = [(Producto, "id_producto")]
            elif isinstance(entity, ProductoVariante):
                references = [(Producto, "id_producto")]
            elif isinstance(entity, Suscripcion):
                references = [(Plan, "plan_id"), (Usuario, "creado_por_id")]
            for model, key in references:
                if not belongs(model, key, getattr(entity, key, None)):
                    raise ValueError(f"La relación {key} no pertenece a la organización autenticada")

    @event.listens_for(Session, "before_flush")
    def audit_business_mutations(session, _flush_context, _instances):
        if session.info.get("skip_business_audit"):
            return
        from app.models.audit_log import AuditLog
        from app.services.audit_service import AuditService
        from app.models.inventario import Inventario
        from app.models.pedido import Pedido
        from app.models.pago import Pago
        from app.models.reserva import Reserva
        from app.models.sucursal import Sucursal
        from app.models.producto import Producto
        from app.models.suscripcion import Suscripcion

        watched = (Usuario, Sucursal, Producto, MovimientoInventario, Reserva, Pedido, Pago, Suscripcion)
        for row in tuple(session.new) + tuple(session.dirty):
            if isinstance(row, AuditLog) or not isinstance(row, watched):
                continue
            state = inspect(row)
            is_new = row in session.new
            changed = [attr.key for attr in state.mapper.column_attrs
                       if state.attrs[attr.key].history.has_changes()]
            if not is_new and not changed:
                continue
            org_id = getattr(row, "id_organizacion", None) or getattr(row, "organizacion_id", None)
            if org_id is None and isinstance(row, MovimientoInventario):
                inv = session.get(Inventario, row.id_inventario)
                org_id = inv.sucursal.id_organizacion if inv and inv.sucursal else None
            elif org_id is None and isinstance(row, Reserva):
                usr = session.get(Usuario, row.id_usuario)
                org_id = usr.id_organizacion if usr else None
            elif org_id is None and isinstance(row, Pedido):
                usr = session.get(Usuario, row.id_vendedor) if row.id_vendedor else None
                if usr is None and row.id_cliente:
                    from app.models.cliente import Cliente
                    client = session.get(Cliente, row.id_cliente)
                    usr = session.get(Usuario, client.id_usuario) if client else None
                org_id = usr.id_organizacion if usr else None
            elif org_id is None and isinstance(row, Pago):
                order = session.get(Pedido, row.id_pedido) if row.id_pedido else None
                usr = session.get(Usuario, order.id_vendedor) if order and order.id_vendedor else None
                if usr is None and order and order.id_cliente:
                    from app.models.cliente import Cliente
                    client = session.get(Cliente, order.id_cliente)
                    usr = session.get(Usuario, client.id_usuario) if client else None
                org_id = usr.id_organizacion if usr else None
            if not org_id:
                continue
            safe_details = {"campos": sorted(changed)}
            if "estado" in changed:
                hist = state.attrs.estado.history
                safe_details["estado_anterior"] = hist.deleted[0] if hist.deleted else None
                safe_details["estado_nuevo"] = hist.added[0] if hist.added else getattr(row, "estado", None)
            actor_id = session.info.get("audit_actor_id")
            actor_role = session.info.get("audit_actor_role", "SISTEMA")
            event_names = {
                Usuario: ("USUARIO_CREADO", "USUARIO_MODIFICADO"),
                Sucursal: ("SUCURSAL_CREADA", "SUCURSAL_MODIFICADA"),
                Producto: ("PRODUCTO_CREADO", "PRODUCTO_MODIFICADO"),
                MovimientoInventario: ("MOVIMIENTO_INVENTARIO_REGISTRADO", "MOVIMIENTO_INVENTARIO_REGISTRADO"),
                Reserva: ("RESERVA_CREADA", "RESERVA_MODIFICADA"),
                Pedido: ("PEDIDO_CREADO", "PEDIDO_MODIFICADO"),
                Pago: ("ESTADO_PAGO_CAMBIADO", "ESTADO_PAGO_CAMBIADO"),
                PaymentRefund: ("DEVOLUCION_MONETARIA_CREADA", "DEVOLUCION_MONETARIA_ACTUALIZADA"),
                PaymentAdjustment: ("AJUSTE_COBRO_CAMBIO_CREADO", "AJUSTE_COBRO_CAMBIO_ACTUALIZADO"),
                Suscripcion: ("SUSCRIPCION_ASIGNADA", "SUSCRIPCION_MODIFICADA"),
            }
            action = event_names[type(row)][0 if is_new else 1]
            if isinstance(row, Pago) and not is_new and "estado" not in changed:
                continue
            if isinstance(row, MovimientoInventario) and not is_new:
                continue
            # Subscription transitions are audited explicitly by the lifecycle service
            # so they receive semantic actions and idempotency keys.
            if isinstance(row, Suscripcion):
                continue
            entity_id = (getattr(row, "id_usuario", None) or getattr(row, "id_sucursal", None)
                         or getattr(row, "id_producto", None) or getattr(row, "id_movimiento", None)
                         or getattr(row, "id_reserva", None) or getattr(row, "id_pedido", None)
                         or getattr(row, "id_pago", None) or getattr(row, "id_suscripcion", None))
            entity_id = entity_id or getattr(row, "id", None)
            audit_row = AuditService.record(
                session, organization_id=org_id, actor_id=actor_id, actor_role=actor_role,
                action=action, entity=type(row).__name__, entity_id=entity_id,
                result="EXITOSO", details=safe_details,
            )
            if entity_id is None:
                session.info.setdefault("audit_pending_entity_ids", []).append((audit_row, row))

    @event.listens_for(Session, "after_flush_postexec")
    def set_audited_entity_ids(session, _flush_context):
        pending = session.info.pop("audit_pending_entity_ids", [])
        for audit_row, entity in pending:
            state = inspect(entity)
            if state.identity:
                value = str(state.identity[0])
                session.info.setdefault("audit_internal_entity_ids", {})[id(audit_row)] = value
                audit_row.entidad_id = value

    @event.listens_for(Session, "before_flush")
    def keep_audit_logs_immutable(session, _flush_context, _instances):
        from app.models.audit_log import AuditLog
        internal = session.info.get("audit_internal_entity_ids", {})
        for row in session.dirty.union(session.deleted):
            if not isinstance(row, AuditLog):
                continue
            state = inspect(row)
            expected = internal.get(id(row))
            changed = {attr.key for attr in state.mapper.column_attrs if state.attrs[attr.key].history.has_changes()}
            if row not in session.deleted and expected is not None and changed == {"entidad_id"} and row.entidad_id == expected:
                continue
            raise ValueError("Los registros de auditoría son inmutables")

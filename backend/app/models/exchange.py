from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OrganizationHoliday(Base):
    __tablename__ = "organization_holiday"
    __table_args__ = (UniqueConstraint("organization_id", "holiday_date", name="uq_org_holiday_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizacion.id_organizacion", ondelete="CASCADE"), nullable=False, index=True)
    holiday_date: Mapped[date] = mapped_column(Date, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)


class GarmentExchange(Base):
    __tablename__ = "garment_exchange"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_garment_exchange_quantity"),
        UniqueConstraint("organization_id", "operation_uuid", name="uq_exchange_org_operation"),
        Index("ix_exchange_org_state", "organization_id", "state"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizacion.id_organizacion", ondelete="RESTRICT"), nullable=False, index=True)
    operation_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("cliente.id_cliente"), nullable=False, index=True)
    original_order_id: Mapped[int] = mapped_column(ForeignKey("pedido.id_pedido"), nullable=False, index=True)
    original_detail_id: Mapped[int] = mapped_column(ForeignKey("pedido_detalle.id_detalle"), nullable=False)
    original_variant_id: Mapped[int] = mapped_column(ForeignKey("producto_variante.id_variante"), nullable=False)
    replacement_variant_id: Mapped[int | None] = mapped_column(ForeignKey("producto_variante.id_variante"))
    branch_id: Mapped[int] = mapped_column(ForeignKey("sucursal.id_sucursal"), nullable=False, index=True)
    replacement_branch_id: Mapped[int | None] = mapped_column(ForeignKey("sucursal.id_sucursal"), index=True)
    original_inventory_id: Mapped[int | None] = mapped_column(ForeignKey("inventario.id_inventario"))
    replacement_inventory_id: Mapped[int | None] = mapped_column(ForeignKey("inventario.id_inventario"))
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id_usuario"))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    purchase_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivery_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    inspection_state: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDIENTE")
    garment_good_condition: Mapped[bool] = mapped_column(nullable=False, default=False)
    original_tag_present: Mapped[bool] = mapped_column(nullable=False, default=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="SOLICITADO", index=True)
    original_paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    replacement_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    economic_difference: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    financial_state: Mapped[str] = mapped_column(String(40), nullable=False, default="SIN_DIFERENCIA")
    physical_original_received: Mapped[bool] = mapped_column(nullable=False, default=False)
    physical_replacement_delivered: Mapped[bool] = mapped_column(nullable=False, default=False)
    reconciliation_note: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExchangeInventoryIncident(Base):
    __tablename__ = "exchange_inventory_incident"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_exchange_incident_quantity"),
        CheckConstraint("direction IN ('SALIDA_FISICA', 'ENTRADA_FISICA')", name="ck_exchange_incident_direction"),
        UniqueConstraint("organization_id", "operation_uuid", "variant_id", "direction", name="uq_exchange_incident_operation_line"),
        Index("ix_exchange_incident_org_state", "organization_id", "state"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizacion.id_organizacion", ondelete="RESTRICT"), nullable=False, index=True)
    exchange_id: Mapped[int] = mapped_column(ForeignKey("garment_exchange.id", ondelete="RESTRICT"), nullable=False, index=True)
    operation_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    branch_id: Mapped[int] = mapped_column(ForeignKey("sucursal.id_sucursal"), nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"), nullable=False)
    variant_id: Mapped[int] = mapped_column(ForeignKey("producto_variante.id_variante"), nullable=False)
    inventory_id: Mapped[int | None] = mapped_column(ForeignKey("inventario.id_inventario"))
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="INCIDENCIA_CONCILIACION")
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    resolution_note: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("usuario.id_usuario"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

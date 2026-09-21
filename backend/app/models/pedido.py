from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Pedido(Base):
    __tablename__ = "pedido"

    id_pedido: Mapped[int] = mapped_column(primary_key=True)
    id_cliente: Mapped[int | None] = mapped_column(ForeignKey("cliente.id_cliente"), nullable=True, index=True)
    id_vendedor: Mapped[int | None] = mapped_column(ForeignKey("usuario.id_usuario"), nullable=True, index=True)
    fecha_pedido: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDIENTE")
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tipo_cliente: Mapped[str] = mapped_column(String(30), nullable=False, default="CLIENTE_REGISTRADO")
    tipo_venta: Mapped[str] = mapped_column(String(30), nullable=False, default="ONLINE")
    nit_ci: Mapped[str | None] = mapped_column(String(30))
    razon_social: Mapped[str | None] = mapped_column(String(150))
    tipo_entrega: Mapped[str | None] = mapped_column(String(30))
    id_sucursal_entrega: Mapped[int | None] = mapped_column(ForeignKey("sucursal.id_sucursal"))
    direccion_entrega: Mapped[str | None] = mapped_column(String(255))
    referencia_entrega: Mapped[str | None] = mapped_column(String(255))
    telefono_entrega: Mapped[str | None] = mapped_column(String(30))

    cliente: Mapped["Cliente"] = relationship()
    detalles: Mapped[list["PedidoDetalle"]] = relationship(back_populates="pedido")

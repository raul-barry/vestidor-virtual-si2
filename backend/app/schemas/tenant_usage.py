from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class TenantUsageResponse(BaseModel):
    organizacion_id: int
    organizacion_nombre: str
    periodo_desde: date | None
    periodo_hasta: date | None
    plan_codigo: str | None
    plan_nombre: str | None
    estado_suscripcion: str
    fecha_inicio_suscripcion: datetime | None
    fecha_fin_suscripcion: datetime | None
    sucursales_activas: int
    limite_sucursales: int | None
    usuarios_activos: int
    productos_registrados: int
    pedidos_periodo: int
    ventas_periodo: Decimal
    reservas_periodo: int
    inventario_disponible: int
    inventario_reservado: int
    inventario_vendido: int

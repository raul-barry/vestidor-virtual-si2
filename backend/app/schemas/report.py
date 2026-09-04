from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class DashboardReportResponse(BaseModel):
    usuarios_totales: int
    clientes_totales: int
    productos_totales: int
    pedidos_totales: int
    ventas_totales: Decimal
    productos_stock_bajo: int


class SalesReportResponse(BaseModel):
    ventas_totales: Decimal
    cantidad_pedidos: int
    promedio_compra: Decimal
    pedidos_por_estado: dict[str, int]


class ProductRankingResponse(BaseModel):
    producto: str
    cantidad_vendida: int
    ingresos_generados: Decimal


class CategoryRankingResponse(BaseModel):
    categoria: str
    cantidad_vendida: int
    ventas_generadas: Decimal


class RecentInventoryMovementResponse(BaseModel):
    producto: str
    tipo: str
    cantidad: int
    fecha: datetime


class InventoryReportResponse(BaseModel):
    stock_total: int
    productos_stock_bajo: int
    productos_sin_stock: int
    movimientos_recientes: list[RecentInventoryMovementResponse]


class CustomerReportResponse(BaseModel):
    usuarios_registrados: int
    clientes_activos: int
    clientes_nuevos_mes: int
    clientes_con_compras: int

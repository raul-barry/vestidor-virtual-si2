from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator


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


class ReportBranchResponse(BaseModel):
    id_sucursal: int
    nombre: str


class BranchComparisonAccessResponse(BaseModel):
    comparacion_sucursales: bool
    exportacion_pdf_excel: bool


class BranchSalesComparisonRow(BaseModel):
    id_sucursal: int
    sucursal: str
    ranking: int
    ingresos_netos: Decimal
    cantidad_ventas: int
    ticket_promedio: Decimal
    ingresos_periodo_anterior: Decimal
    ventas_periodo_anterior: int
    variacion_porcentual: Decimal | None


class BranchSalesComparisonResponse(BaseModel):
    organizacion: str
    periodo: dict[str, date]
    periodo_anterior: dict[str, date]
    sucursales: list[BranchSalesComparisonRow]
    totales: dict[str, Decimal | int | None]
    destacados: dict[str, int | None]
    zona_horaria: str


class ReportFeaturesResponse(BaseModel):
    reportes_ia: bool
    reportes_gemini: bool | None = None  # Deprecated compatibility alias.
    reportes_voz: bool
    comparacion_sucursales: bool
    exportacion_pdf_excel: bool


class AiReportRequest(BaseModel):
    tipo: Literal["ventas", "productos", "sucursales", "inventario", "tendencias"]
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    id_sucursal: int | None = Field(default=None, gt=0)
    consulta: str = Field(default="", max_length=500)
    canal: Literal["texto", "voz"] = "texto"

    @model_validator(mode="after")
    def validate_period(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_inicio > self.fecha_fin:
            raise ValueError("fecha_inicio no puede ser posterior a fecha_fin")
        return self


class AiReportResponse(BaseModel):
    tipo: str
    periodo: dict[str, date]
    metricas_calculadas: dict
    observaciones_ia: list[str]
    recomendaciones_ia: list[str]
    error_ia: str | None = None

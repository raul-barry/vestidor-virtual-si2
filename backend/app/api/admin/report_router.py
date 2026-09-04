from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.database.database import get_db
from app.models.usuario import Usuario
from app.schemas.report import (
    CategoryRankingResponse,
    CustomerReportResponse,
    DashboardReportResponse,
    InventoryReportResponse,
    ProductRankingResponse,
    SalesReportResponse,
)
from app.services.report_service import ReportService

report_router = APIRouter(prefix="/admin/reports", tags=["Reportes administrativos"])


@report_router.get("/dashboard", response_model=DashboardReportResponse)
def dashboard(
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_admin)
) -> DashboardReportResponse:
    return ReportService(db).dashboard(current_user.id_usuario)


@report_router.get("/sales", response_model=SalesReportResponse)
def sales(
    fecha_inicio: date | None = Query(default=None),
    fecha_fin: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_admin),
) -> SalesReportResponse:
    return ReportService(db).sales(current_user.id_usuario, fecha_inicio, fecha_fin)


@report_router.get("/top-products", response_model=list[ProductRankingResponse])
def top_products(
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_admin)
) -> list[ProductRankingResponse]:
    return ReportService(db).top_products(current_user.id_usuario)


@report_router.get("/top-categories", response_model=list[CategoryRankingResponse])
def top_categories(
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_admin)
) -> list[CategoryRankingResponse]:
    return ReportService(db).top_categories(current_user.id_usuario)


@report_router.get("/inventory", response_model=InventoryReportResponse)
def inventory(
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_admin)
) -> InventoryReportResponse:
    return ReportService(db).inventory(current_user.id_usuario)


@report_router.get("/customers", response_model=CustomerReportResponse)
def customers(
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_admin)
) -> CustomerReportResponse:
    return ReportService(db).customers(current_user.id_usuario)

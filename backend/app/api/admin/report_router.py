from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.database.database import get_db
from app.models.plan import PlanCaracteristica
from app.models.sucursal import Sucursal
from app.models.usuario import Usuario
from app.schemas.report import AiReportRequest, AiReportResponse, ReportBranchResponse, ReportFeaturesResponse
from app.schemas.report import (
    CategoryRankingResponse,
    CustomerReportResponse,
    DashboardReportResponse,
    InventoryReportResponse,
    ProductRankingResponse,
    SalesReportResponse,
)
from app.services.ai_report_service import AiReportService
from app.services.ai_provider_service import AIProviderError
from app.services.plan_access_service import PlanAccessService
from app.services.report_service import ReportService
from app.services.report_export_service import build_report_export
from app.services.audit_service import AuditService

report_router = APIRouter(prefix="/admin/reports", tags=["Reportes administrativos"])


@report_router.get("/dashboard", response_model=DashboardReportResponse)
def dashboard(
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_admin)
) -> DashboardReportResponse:
    return ReportService(db, current_user.id_organizacion).dashboard(current_user.id_usuario)


@report_router.get("/sales", response_model=SalesReportResponse)
def sales(
    fecha_inicio: date | None = Query(default=None),
    fecha_fin: date | None = Query(default=None),
    id_sucursal: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_admin),
) -> SalesReportResponse:
    return ReportService(db, current_user.id_organizacion).sales(
        current_user.id_usuario, fecha_inicio, fecha_fin, id_sucursal
    )


@report_router.get("/top-products", response_model=list[ProductRankingResponse])
def top_products(
    fecha_inicio: date | None = Query(default=None),
    fecha_fin: date | None = Query(default=None),
    id_sucursal: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_admin)
) -> list[ProductRankingResponse]:
    return ReportService(db, current_user.id_organizacion).top_products(
        current_user.id_usuario, fecha_inicio, fecha_fin, id_sucursal
    )


@report_router.get("/top-categories", response_model=list[CategoryRankingResponse])
def top_categories(
    fecha_inicio: date | None = Query(default=None),
    fecha_fin: date | None = Query(default=None),
    id_sucursal: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_admin)
) -> list[CategoryRankingResponse]:
    return ReportService(db, current_user.id_organizacion).top_categories(
        current_user.id_usuario, fecha_inicio, fecha_fin, id_sucursal
    )


@report_router.get("/inventory", response_model=InventoryReportResponse)
def inventory(
    id_sucursal: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_admin)
) -> InventoryReportResponse:
    return ReportService(db, current_user.id_organizacion).inventory(
        current_user.id_usuario, id_sucursal
    )


@report_router.get("/customers", response_model=CustomerReportResponse)
def customers(
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_admin)
) -> CustomerReportResponse:
    return ReportService(db, current_user.id_organizacion).customers(current_user.id_usuario)


@report_router.get("/branches", response_model=list[ReportBranchResponse])
def branches(
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_admin)
) -> list[ReportBranchResponse]:
    rows = db.execute(select(Sucursal.id_sucursal, Sucursal.nombre).where(
        Sucursal.id_organizacion == current_user.id_organizacion,
        Sucursal.estado == "ACTIVA",
    ).order_by(Sucursal.nombre)).all()
    return [ReportBranchResponse(id_sucursal=row[0], nombre=row[1]) for row in rows]


@report_router.get("/features", response_model=ReportFeaturesResponse)
def report_features(
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_admin)
) -> ReportFeaturesResponse:
    access = PlanAccessService(db).resolve()
    if not access.has_subscription_history:
        return ReportFeaturesResponse(reportes_gemini=True, reportes_voz=True,
                                      comparacion_sucursales=True, exportacion_pdf_excel=True)
    if access.subscription is None:
        return ReportFeaturesResponse(reportes_gemini=False, reportes_voz=False,
                                      comparacion_sucursales=False, exportacion_pdf_excel=False)
    enabled = set(db.scalars(select(PlanCaracteristica.codigo).where(
        PlanCaracteristica.plan_id == access.subscription.plan_id,
        PlanCaracteristica.habilitada.is_(True),
    )).all())
    return ReportFeaturesResponse(
        reportes_gemini="reportes_gemini" in enabled,
        reportes_voz="reportes_voz" in enabled,
        comparacion_sucursales="comparacion_sucursales" in enabled,
        exportacion_pdf_excel="exportacion_pdf_excel" in enabled,
    )


@report_router.post("/ai", response_model=AiReportResponse)
def ai_report(
    request: AiReportRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_admin),
) -> AiReportResponse:
    plan_access = PlanAccessService(db)
    plan_access.require_feature("reportes_gemini")
    if request.canal == "voz":
        plan_access.require_feature("reportes_voz")
    if request.tipo == "sucursales":
        plan_access.require_feature("comparacion_sucursales")
    try:
        return AiReportService(db).generate(current_user, request)
    except AIProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@report_router.post("/export/{file_format}")
def export_report(
    file_format: Literal["pdf", "xlsx"],
    request: AiReportRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_admin),
) -> Response:
    PlanAccessService(db).require_feature("exportacion_pdf_excel")
    service = AiReportService(db)
    start, end, metrics = service.calculate(request)
    branch_name = ""
    if request.id_sucursal is not None:
        branch_name = db.scalar(select(Sucursal.nombre).where(
            Sucursal.id_sucursal == request.id_sucursal,
            Sucursal.id_organizacion == current_user.id_organizacion,
        )) or ""
    content, media_type, filename = build_report_export(
        file_format, request.tipo, start, end, branch_name, metrics
    )
    AuditService.record(
        db,
        organization_id=current_user.id_organizacion,
        actor_id=current_user.id_usuario,
        actor_role=current_user.rol.nombre,
        action="REPORTE_EXPORTADO",
        entity="Reporte",
        entity_id=request.tipo,
        details={
            "formato": file_format,
            "desde": start.isoformat(),
            "hasta": end.isoformat(),
            "id_sucursal": request.id_sucursal,
        },
    )
    db.commit()
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )

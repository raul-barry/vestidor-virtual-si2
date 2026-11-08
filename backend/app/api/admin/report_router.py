from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_admin, get_current_report_comparison_user, get_current_user
from app.database.database import get_db
from app.models.plan import PlanCaracteristica
from app.models.sucursal import Sucursal
from app.models.organizacion import Organizacion
from app.models.usuario import Usuario
from app.schemas.report import AiReportRequest, AiReportResponse, ReportBranchResponse, ReportFeaturesResponse
from app.schemas.report import (
    BranchComparisonAccessResponse,
    BranchSalesComparisonResponse,
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


def _comparison_scope(db: Session, user: Usuario, selected: list[int] | None = None) -> list[int] | None:
    if user.id_organizacion is None:
        raise HTTPException(status_code=403, detail="Los reportes comerciales requieren una organización")
    if user.rol.nombre == "ADMINISTRADOR":
        return selected or None
    if selected and any(branch_id <= 0 for branch_id in selected):
        raise HTTPException(status_code=422, detail="Identificador de sucursal no válido")
    if user.id_sucursal is None:
        raise HTTPException(status_code=403, detail="El usuario no tiene sucursal asignada")
    if selected and any(branch_id != user.id_sucursal for branch_id in selected):
        raise HTTPException(status_code=403, detail="Sucursal fuera del alcance asignado")
    branch = db.scalar(select(Sucursal.id_sucursal).where(
        Sucursal.id_sucursal == user.id_sucursal,
        Sucursal.id_organizacion == user.id_organizacion,
        Sucursal.estado == "ACTIVA",
    ))
    if branch is None:
        raise HTTPException(status_code=403, detail="La sucursal asignada no pertenece a la organización activa")
    return [user.id_sucursal]


@report_router.get("/comparison/access", response_model=BranchComparisonAccessResponse)
def comparison_access(
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user),
) -> BranchComparisonAccessResponse:
    if current_user.id_organizacion is None:
        return BranchComparisonAccessResponse(comparacion_sucursales=False, exportacion_pdf_excel=False)
    role_allowed = current_user.rol.nombre == "ADMINISTRADOR" or (
        current_user.rol.nombre in {"ENCARGADO_SUCURSAL", "ENCARGADO", "GERENTE"}
        and current_user.id_sucursal is not None
        and any(permission.codigo == "REPORTES_COMPARATIVOS" for permission in current_user.rol.permisos)
    )
    if not role_allowed:
        return BranchComparisonAccessResponse(comparacion_sucursales=False, exportacion_pdf_excel=False)
    if current_user.rol.nombre != "ADMINISTRADOR":
        assigned_branch = db.scalar(select(Sucursal.id_sucursal).where(
            Sucursal.id_sucursal == current_user.id_sucursal,
            Sucursal.id_organizacion == current_user.id_organizacion,
            Sucursal.estado == "ACTIVA",
        ))
        if assigned_branch is None:
            return BranchComparisonAccessResponse(comparacion_sucursales=False, exportacion_pdf_excel=False)
    access = PlanAccessService(db).resolve()
    if not access.has_subscription_history:
        return BranchComparisonAccessResponse(comparacion_sucursales=True, exportacion_pdf_excel=True)
    if access.subscription is None:
        return BranchComparisonAccessResponse(comparacion_sucursales=False, exportacion_pdf_excel=False)
    feature_codes = set(db.scalars(select(PlanCaracteristica.codigo).where(
        PlanCaracteristica.plan_id == access.subscription.plan_id,
        PlanCaracteristica.habilitada.is_(True),
        PlanCaracteristica.codigo.in_(("comparacion_sucursales", "exportacion_pdf_excel")),
    )).all())
    return BranchComparisonAccessResponse(
        comparacion_sucursales="comparacion_sucursales" in feature_codes,
        exportacion_pdf_excel="exportacion_pdf_excel" in feature_codes,
    )


@report_router.get("/comparison/branches", response_model=list[ReportBranchResponse])
def comparison_branches(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_report_comparison_user),
) -> list[ReportBranchResponse]:
    PlanAccessService(db).require_feature("comparacion_sucursales")
    scope = _comparison_scope(db, current_user)
    statement = select(Sucursal.id_sucursal, Sucursal.nombre).where(
        Sucursal.id_organizacion == current_user.id_organizacion,
        Sucursal.estado == "ACTIVA",
    )
    if scope is not None:
        statement = statement.where(Sucursal.id_sucursal.in_(scope))
    rows = db.execute(statement.order_by(Sucursal.nombre)).all()
    return [ReportBranchResponse(id_sucursal=row[0], nombre=row[1]) for row in rows]


@report_router.get("/comparison", response_model=BranchSalesComparisonResponse)
def branch_sales_comparison(
    fecha_inicio: date | None = Query(default=None),
    fecha_fin: date | None = Query(default=None),
    id_sucursal: list[int] | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_report_comparison_user),
) -> BranchSalesComparisonResponse:
    PlanAccessService(db).require_feature("comparacion_sucursales")
    scope = _comparison_scope(db, current_user, id_sucursal)
    organization = db.get(Organizacion, current_user.id_organizacion)
    if organization is None:
        raise HTTPException(status_code=403, detail="Organización no disponible")
    return ReportService(db, current_user.id_organizacion).branch_sales_comparison(
        current_user.id_usuario, organization, fecha_inicio, fecha_fin, scope,
        scoped_branch_id=current_user.id_sucursal if current_user.rol.nombre != "ADMINISTRADOR" else None,
    )


@report_router.get("/comparison/export/{file_format}")
def export_branch_sales_comparison(
    file_format: Literal["pdf", "xlsx"],
    fecha_inicio: date | None = Query(default=None),
    fecha_fin: date | None = Query(default=None),
    id_sucursal: list[int] | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_report_comparison_user),
) -> Response:
    PlanAccessService(db).require_feature("comparacion_sucursales")
    PlanAccessService(db).require_feature("exportacion_pdf_excel")
    scope = _comparison_scope(db, current_user, id_sucursal)
    organization = db.get(Organizacion, current_user.id_organizacion)
    if organization is None:
        raise HTTPException(status_code=403, detail="Organización no disponible")
    result = ReportService(db, current_user.id_organizacion).branch_sales_comparison(
        current_user.id_usuario, organization, fecha_inicio, fecha_fin, scope,
        scoped_branch_id=current_user.id_sucursal if current_user.rol.nombre != "ADMINISTRADOR" else None,
    )
    start = result.periodo["desde"]
    end = result.periodo["hasta"]
    names = ", ".join(row.sucursal for row in result.sucursales)
    metrics = {
        "ventas_pagadas": str(result.totales["ingresos_netos"]),
        "pedidos_pagados": result.totales["cantidad_ventas"],
        "periodo_anterior": {key: value.isoformat() for key, value in result.periodo_anterior.items()},
        "totales": {key: str(value) if value is not None else None for key, value in result.totales.items()},
        "destacados": result.destacados,
        "rendimiento_por_sucursal": [
            {"ranking": row.ranking, "id_sucursal": row.id_sucursal, "sucursal": row.sucursal,
             "ingresos_netos": str(row.ingresos_netos), "cantidad_ventas": row.cantidad_ventas,
             "ticket_promedio": str(row.ticket_promedio),
             "ingresos_periodo_anterior": str(row.ingresos_periodo_anterior),
             "ventas_periodo_anterior": row.ventas_periodo_anterior,
             "variacion_porcentual": str(row.variacion_porcentual) if row.variacion_porcentual is not None else "No disponible"}
            for row in result.sucursales
        ],
    }
    content, media_type, filename = build_report_export(
        file_format, "sucursales", start, end, names, metrics,
        organization_name=organization.nombre, generated_at=datetime.now(timezone.utc),
    )
    AuditService.record(
        db, organization_id=current_user.id_organizacion, actor_id=current_user.id_usuario,
        actor_role=current_user.rol.nombre, action="REPORTE_COMPARATIVO_EXPORTADO",
        entity="ReporteSucursal", entity_id="comparacion_sucursales",
        details={"formato": file_format, "desde": start.isoformat(), "hasta": end.isoformat(),
                 "sucursales": [row.id_sucursal for row in result.sucursales]},
    )
    db.commit()
    return Response(content=content, media_type=media_type, headers={
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
    })


@report_router.get("/features", response_model=ReportFeaturesResponse)
def report_features(
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_admin)
) -> ReportFeaturesResponse:
    access = PlanAccessService(db).resolve()
    if not access.has_subscription_history:
        return ReportFeaturesResponse(reportes_ia=True, reportes_gemini=True, reportes_voz=True,
                                      comparacion_sucursales=True, exportacion_pdf_excel=True)
    if access.subscription is None:
        return ReportFeaturesResponse(reportes_ia=False, reportes_gemini=False, reportes_voz=False,
                                      comparacion_sucursales=False, exportacion_pdf_excel=False)
    plan_codes = set(db.scalars(select(PlanCaracteristica.codigo).where(
        PlanCaracteristica.plan_id == access.subscription.plan_id,
    )).all())
    enabled = set(db.scalars(select(PlanCaracteristica.codigo).where(
        PlanCaracteristica.plan_id == access.subscription.plan_id,
        PlanCaracteristica.habilitada.is_(True),
    )).all())
    reports_ai = "reportes_ia" in enabled if "reportes_ia" in plan_codes else "reportes_gemini" in enabled
    return ReportFeaturesResponse(
        reportes_ia=reports_ai,
        reportes_gemini=reports_ai,
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
    plan_access.require_feature("reportes_ia")
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

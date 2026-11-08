"""Idempotent starter data for commercial plans and their capabilities."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.plan import Plan, PlanCaracteristica


PLAN_DATA = (
    ("ESTILO", "Plan Estilo", "Plan comercial con hasta 2 sucursales.", 2),
    ("MODA", "Plan Moda", "Plan comercial con hasta 10 sucursales.", 10),
    ("GLAMOUR", "Plan Glamour", "Plan comercial sin límite fijo de sucursales.", None),
)

COMMON_FEATURES = (
    ("catalogo", "Catálogo", "Consulta y administración del catálogo."),
    ("inventario", "Inventario", "Control de inventario."),
    ("reservas", "Reservas", "Gestión de reservas."),
    ("ventas", "Ventas", "Registro y consulta de ventas."),
    ("pedidos", "Pedidos", "Gestión de pedidos."),
    ("pagos_simulados", "Pagos simulados", "Pagos en modo de simulación."),
    ("dashboard_basico", "Dashboard básico", "Indicadores comerciales básicos."),
    ("catalogo_offline", "Catálogo offline", "Consulta offline del catálogo."),
)

MODA_FEATURES = (
    ("operaciones_offline", "Operaciones offline", "Registro de operaciones sin conexión."),
    ("sincronizacion", "Sincronización", "Sincronización de operaciones pendientes."),
    ("reportes_ia", "Reportes con IA", "Reportes empresariales asistidos por inteligencia artificial."),
    ("exportacion_pdf_excel", "Exportación PDF y Excel", "Exportación de reportes a PDF y Excel."),
    ("comparacion_sucursales", "Comparación entre sucursales", "Comparación de indicadores entre sucursales."),
)

GLAMOUR_FEATURES = (
    ("reportes_voz", "Reportes por voz", "Consulta de reportes mediante voz."),
    ("machine_learning", "Machine Learning", "Capacidades analíticas basadas en aprendizaje automático."),
    ("prediccion_demanda", "Predicción de demanda", "Estimación de demanda comercial."),
    ("segmentacion_kmeans", "Segmentación K-Means", "Segmentación de clientes mediante K-Means."),
    ("dashboard_predictivo", "Dashboard predictivo", "Indicadores predictivos."),
)


def seed_commercial_plans(db: Session) -> int:
    """Insert missing plans/features, preserving any existing capability settings.

    Returns the number of rows created. The caller owns the transaction.
    """
    created = 0
    plans: dict[str, Plan] = {}
    for code, name, description, max_branches in PLAN_DATA:
        plan = db.scalar(select(Plan).where(Plan.codigo == code))
        if plan is None:
            plan = Plan(codigo=code, nombre=name, descripcion=description, max_sucursales=max_branches)
            db.add(plan)
            db.flush()
            created += 1
        plans[code] = plan

    for code, plan in plans.items():
        features = list(COMMON_FEATURES)
        if code in ("MODA", "GLAMOUR"):
            features.extend(MODA_FEATURES)
        if code == "GLAMOUR":
            features.extend(GLAMOUR_FEATURES)
        existing = set(db.scalars(
            select(PlanCaracteristica.codigo).where(PlanCaracteristica.plan_id == plan.id_plan)
        ).all())
        for feature_code, name, description in features:
            if feature_code in existing:
                continue
            legacy_ai = None
            if feature_code == "reportes_ia" and "reportes_gemini" in existing:
                legacy_ai = db.scalar(select(PlanCaracteristica).where(
                    PlanCaracteristica.plan_id == plan.id_plan,
                    PlanCaracteristica.codigo == "reportes_gemini",
                ))
            db.add(PlanCaracteristica(
                plan_id=plan.id_plan,
                codigo=feature_code,
                nombre=name,
                descripcion=description,
                habilitada=legacy_ai.habilitada if legacy_ai else True,
                limite=legacy_ai.limite if legacy_ai else None,
                configuracion=legacy_ai.configuracion if legacy_ai else None,
            ))
            created += 1

    db.flush()
    return created

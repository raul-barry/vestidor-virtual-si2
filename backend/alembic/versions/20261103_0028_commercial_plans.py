"""Create configurable SaaS plans and seed the initial plan matrix."""

from alembic import op
import sqlalchemy as sa


revision = "20261103_0028"
down_revision = "20261103_0027"
branch_labels = None
depends_on = None


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
    ("reportes_gemini", "Reportes Gemini", "Reportes asistidos por Gemini."),
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


def upgrade() -> None:
    op.create_table(
        "plan",
        sa.Column("id_plan", sa.Integer(), primary_key=True),
        sa.Column("codigo", sa.String(length=40), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("max_sucursales", sa.Integer(), nullable=True),
        sa.Column("activo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("codigo", name="uq_plan_codigo"),
        sa.CheckConstraint("max_sucursales IS NULL OR max_sucursales > 0", name="ck_plan_max_sucursales_positivo"),
    )
    op.create_table(
        "plan_caracteristica",
        sa.Column("id_plan_caracteristica", sa.Integer(), primary_key=True),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("plan.id_plan", ondelete="CASCADE"), nullable=False),
        sa.Column("codigo", sa.String(length=80), nullable=False),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("habilitada", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("limite", sa.Integer(), nullable=True),
        sa.Column("configuracion", sa.JSON(), nullable=True),
        sa.UniqueConstraint("plan_id", "codigo", name="uq_plan_caracteristica_plan_codigo"),
        sa.CheckConstraint("limite IS NULL OR limite >= 0", name="ck_plan_caracteristica_limite_no_negativo"),
    )
    op.create_index("ix_plan_caracteristica_plan_id", "plan_caracteristica", ["plan_id"])

    bind = op.get_bind()
    plans = sa.table("plan", sa.column("id_plan", sa.Integer), sa.column("codigo", sa.String),
                     sa.column("nombre", sa.String), sa.column("descripcion", sa.Text),
                     sa.column("max_sucursales", sa.Integer), sa.column("activo", sa.Boolean))
    plan_rows = (
        {"codigo": "ESTILO", "nombre": "Plan Estilo", "descripcion": "Plan comercial con hasta 2 sucursales.", "max_sucursales": 2, "activo": True},
        {"codigo": "MODA", "nombre": "Plan Moda", "descripcion": "Plan comercial con hasta 10 sucursales.", "max_sucursales": 10, "activo": True},
        {"codigo": "GLAMOUR", "nombre": "Plan Glamour", "descripcion": "Plan comercial sin límite fijo de sucursales.", "max_sucursales": None, "activo": True},
    )
    op.bulk_insert(plans, list(plan_rows))

    feature_table = sa.table(
        "plan_caracteristica", sa.column("plan_id", sa.Integer), sa.column("codigo", sa.String),
        sa.column("nombre", sa.String), sa.column("descripcion", sa.Text), sa.column("habilitada", sa.Boolean),
    )
    feature_rows = []
    plan_ids = {code: plan_id for plan_id, code in bind.execute(sa.select(plans.c.id_plan, plans.c.codigo))}
    for code, extra_features in (("ESTILO", ()), ("MODA", MODA_FEATURES), ("GLAMOUR", MODA_FEATURES + GLAMOUR_FEATURES)):
        plan_id = plan_ids[code]
        for code, name, description in COMMON_FEATURES + extra_features:
            feature_rows.append({"plan_id": plan_id, "codigo": code, "nombre": name,
                                 "descripcion": description, "habilitada": True})
    op.bulk_insert(feature_table, feature_rows)


def downgrade() -> None:
    op.drop_index("ix_plan_caracteristica_plan_id", table_name="plan_caracteristica")
    op.drop_table("plan_caracteristica")
    op.drop_table("plan")

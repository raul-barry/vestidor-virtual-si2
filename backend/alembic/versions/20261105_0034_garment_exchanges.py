"""Persist garment exchanges, physical reconciliation and organization holidays."""
from alembic import op
import sqlalchemy as sa

revision = "20261105_0034"
down_revision = "20261104_0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pedido", sa.Column("fecha_entrega", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "organization_holiday",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizacion.id_organizacion", ondelete="CASCADE"), nullable=False),
        sa.Column("holiday_date", sa.Date(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.UniqueConstraint("organization_id", "holiday_date", name="uq_org_holiday_date"),
    )
    op.create_index("ix_organization_holiday_organization_id", "organization_holiday", ["organization_id"])
    op.create_table(
        "garment_exchange",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizacion.id_organizacion", ondelete="RESTRICT"), nullable=False),
        sa.Column("operation_uuid", sa.String(36), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("cliente.id_cliente"), nullable=False),
        sa.Column("original_order_id", sa.Integer(), sa.ForeignKey("pedido.id_pedido"), nullable=False),
        sa.Column("original_detail_id", sa.Integer(), sa.ForeignKey("pedido_detalle.id_detalle"), nullable=False),
        sa.Column("original_variant_id", sa.Integer(), sa.ForeignKey("producto_variante.id_variante"), nullable=False),
        sa.Column("replacement_variant_id", sa.Integer(), sa.ForeignKey("producto_variante.id_variante")),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), nullable=False),
        sa.Column("replacement_branch_id", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal")),
        sa.Column("original_inventory_id", sa.Integer(), sa.ForeignKey("inventario.id_inventario")),
        sa.Column("replacement_inventory_id", sa.Integer(), sa.ForeignKey("inventario.id_inventario")),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("usuario.id_usuario")),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("purchase_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivery_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("inspection_state", sa.String(30), nullable=False, server_default="PENDIENTE"),
        sa.Column("garment_good_condition", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("original_tag_present", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("state", sa.String(40), nullable=False, server_default="SOLICITADO"),
        sa.Column("original_paid_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("replacement_amount", sa.Numeric(12, 2)),
        sa.Column("economic_difference", sa.Numeric(12, 2)),
        sa.Column("financial_state", sa.String(40), nullable=False, server_default="SIN_DIFERENCIA"),
        sa.Column("physical_original_received", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("physical_replacement_delivered", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reconciliation_note", sa.Text()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("quantity > 0", name="ck_garment_exchange_quantity"),
        sa.UniqueConstraint("organization_id", "operation_uuid", name="uq_exchange_org_operation"),
    )
    op.create_index("ix_garment_exchange_organization_id", "garment_exchange", ["organization_id"])
    op.create_index("ix_garment_exchange_customer_id", "garment_exchange", ["customer_id"])
    op.create_index("ix_garment_exchange_original_order_id", "garment_exchange", ["original_order_id"])
    op.create_index("ix_garment_exchange_branch_id", "garment_exchange", ["branch_id"])
    op.create_index("ix_garment_exchange_state", "garment_exchange", ["state"])
    op.create_index("ix_garment_exchange_replacement_branch_id", "garment_exchange", ["replacement_branch_id"])
    op.create_index("ix_exchange_org_state", "garment_exchange", ["organization_id", "state"])
    op.create_table(
        "exchange_inventory_incident",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizacion.id_organizacion", ondelete="RESTRICT"), nullable=False),
        sa.Column("exchange_id", sa.Integer(), sa.ForeignKey("garment_exchange.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("operation_uuid", sa.String(36), nullable=False),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("sucursal.id_sucursal"), nullable=False),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("usuario.id_usuario"), nullable=False),
        sa.Column("variant_id", sa.Integer(), sa.ForeignKey("producto_variante.id_variante"), nullable=False),
        sa.Column("inventory_id", sa.Integer(), sa.ForeignKey("inventario.id_inventario")),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(40), nullable=False, server_default="INCIDENCIA_CONCILIACION"),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("resolution_note", sa.Text()),
        sa.Column("resolved_by", sa.Integer(), sa.ForeignKey("usuario.id_usuario")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("quantity > 0", name="ck_exchange_incident_quantity"),
        sa.CheckConstraint("direction IN ('SALIDA_FISICA', 'ENTRADA_FISICA')", name="ck_exchange_incident_direction"),
        sa.UniqueConstraint("organization_id", "operation_uuid", "variant_id", "direction", name="uq_exchange_incident_operation_line"),
    )
    op.create_index("ix_exchange_inventory_incident_organization_id", "exchange_inventory_incident", ["organization_id"])
    op.create_index("ix_exchange_inventory_incident_exchange_id", "exchange_inventory_incident", ["exchange_id"])
    op.create_index("ix_exchange_incident_org_state", "exchange_inventory_incident", ["organization_id", "state"])


def downgrade() -> None:
    op.drop_index("ix_exchange_incident_org_state", table_name="exchange_inventory_incident")
    op.drop_index("ix_exchange_inventory_incident_exchange_id", table_name="exchange_inventory_incident")
    op.drop_index("ix_exchange_inventory_incident_organization_id", table_name="exchange_inventory_incident")
    op.drop_table("exchange_inventory_incident")
    op.drop_index("ix_exchange_org_state", table_name="garment_exchange")
    op.drop_index("ix_garment_exchange_state", table_name="garment_exchange")
    op.drop_index("ix_garment_exchange_replacement_branch_id", table_name="garment_exchange")
    op.drop_index("ix_garment_exchange_branch_id", table_name="garment_exchange")
    op.drop_index("ix_garment_exchange_original_order_id", table_name="garment_exchange")
    op.drop_index("ix_garment_exchange_customer_id", table_name="garment_exchange")
    op.drop_index("ix_garment_exchange_organization_id", table_name="garment_exchange")
    op.drop_table("garment_exchange")
    op.drop_index("ix_organization_holiday_organization_id", table_name="organization_holiday")
    op.drop_table("organization_holiday")
    op.drop_column("pedido", "fecha_entrega")

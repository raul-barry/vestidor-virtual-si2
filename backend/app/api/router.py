from fastapi import APIRouter
from app.api.reservation_router import reservation_router
from app.api.commerce_router import commerce_router
from app.api.experience_router import experience_router

from app.api.auth_router import auth_router
from app.api.admin.category_admin_router import category_admin_router
from app.api.admin.product_admin_router import product_admin_router
from app.api.admin.inventory_admin_router import inventory_admin_router
from app.api.admin.order_admin_router import order_admin_router
from app.api.admin.report_router import report_router
from app.api.admin.predictive_router import predictive_router
from app.api.admin.variant_admin_router import variant_admin_router
from app.api.admin.user_admin_router import user_admin_router
from app.api.admin.size_admin_router import size_admin_router
from app.api.admin.color_admin_router import color_admin_router
from app.api.admin.branch_admin_router import branch_admin_router
from app.api.catalog_router import catalog_router
from app.api.cart_router import cart_router
from app.api.order_router import order_router
from app.api.payment_router import payment_router
from app.api.user_router import user_router
from app.api.body_profile_router import body_profile_router
from app.api.admin.role_admin_router import role_admin_router
from app.api.admin.commercial_master_admin_router import commercial_master_admin_router
from app.api.admin.organization_admin_router import organization_admin_router
from app.api.subscription_router import subscription_router
from app.api.admin.plan_admin_router import plan_admin_router
from app.api.tenant_usage_router import tenant_usage_router
from app.api.audit_router import audit_router
from app.api.sync_router import sync_router
from app.api.exchange_router import exchange_router
from app.api.platform_ai_router import platform_ai_router

api_router = APIRouter()
api_router.include_router(reservation_router, prefix="/api")
api_router.include_router(commerce_router, prefix="/api")
api_router.include_router(experience_router, prefix="/api")
api_router.include_router(auth_router, prefix="/api")
api_router.include_router(category_admin_router, prefix="/api")
api_router.include_router(size_admin_router, prefix="/api")
api_router.include_router(color_admin_router, prefix="/api")
api_router.include_router(branch_admin_router, prefix="/api")
api_router.include_router(product_admin_router, prefix="/api")
api_router.include_router(inventory_admin_router, prefix="/api")
api_router.include_router(order_admin_router, prefix="/api")
api_router.include_router(report_router, prefix="/api")
api_router.include_router(predictive_router, prefix="/api")
api_router.include_router(variant_admin_router, prefix="/api")
api_router.include_router(user_admin_router, prefix="/api")
api_router.include_router(catalog_router, prefix="/api")
api_router.include_router(cart_router, prefix="/api")
api_router.include_router(order_router, prefix="/api")
api_router.include_router(payment_router, prefix="/api")
api_router.include_router(user_router, prefix="/api")
api_router.include_router(body_profile_router, prefix="/api")
api_router.include_router(role_admin_router, prefix="/api")
api_router.include_router(commercial_master_admin_router, prefix="/api")
api_router.include_router(organization_admin_router, prefix="/api")
api_router.include_router(subscription_router, prefix="/api")
api_router.include_router(plan_admin_router, prefix="/api")
api_router.include_router(tenant_usage_router, prefix="/api")
api_router.include_router(audit_router, prefix="/api")
api_router.include_router(sync_router, prefix="/api")
api_router.include_router(exchange_router, prefix="/api")
api_router.include_router(platform_ai_router, prefix="/api")


@api_router.get("/")
def root() -> dict:
    return {"message": "API funcionando correctamente"}


@api_router.get("/health")
def health_check() -> dict:
    return {"status": "ok"}

from app.api.experience_router import recommendations
api_router.add_api_route("/api/recommendations", recommendations, methods=["GET"], tags=["Recomendaciones"])

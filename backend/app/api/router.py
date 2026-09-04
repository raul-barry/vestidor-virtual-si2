from fastapi import APIRouter

from app.api.auth_router import auth_router
from app.api.admin.product_admin_router import product_admin_router
from app.api.admin.inventory_admin_router import inventory_admin_router
from app.api.admin.order_admin_router import order_admin_router
from app.api.admin.report_router import report_router
from app.api.admin.variant_admin_router import variant_admin_router
from app.api.admin.user_admin_router import user_admin_router
from app.api.catalog_router import catalog_router
from app.api.cart_router import cart_router
from app.api.order_router import order_router
from app.api.payment_router import payment_router
from app.api.user_router import user_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/api")
api_router.include_router(product_admin_router, prefix="/api")
api_router.include_router(inventory_admin_router, prefix="/api")
api_router.include_router(order_admin_router, prefix="/api")
api_router.include_router(report_router, prefix="/api")
api_router.include_router(variant_admin_router, prefix="/api")
api_router.include_router(user_admin_router, prefix="/api")
api_router.include_router(catalog_router, prefix="/api")
api_router.include_router(cart_router, prefix="/api")
api_router.include_router(order_router, prefix="/api")
api_router.include_router(payment_router, prefix="/api")
api_router.include_router(user_router, prefix="/api")


@api_router.get("/")
def root() -> dict:
    return {"message": "API funcionando correctamente"}


@api_router.get("/health")
def health_check() -> dict:
    return {"status": "ok"}

from datetime import date
from decimal import Decimal
from sqlalchemy import select, func
from app.models.comercio import Promocion


def current_price(db, product):
    today = date.today()
    discount = db.scalar(select(func.max(Promocion.descuento)).where(
        Promocion.id_producto == product.id_producto, Promocion.estado == "ACTIVO",
        Promocion.inicio <= today, Promocion.fin >= today)) or Decimal("0")
    return (product.precio_base * (1 - discount / Decimal("100"))).quantize(Decimal("0.01"))

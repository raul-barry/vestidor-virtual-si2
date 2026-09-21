from sqlalchemy import select
from app.models.producto_variante import ProductoVariante
from app.services.pricing_service import current_price

def available_variants(db):
    return [v for v in db.scalars(select(ProductoVariante).where(ProductoVariante.estado == "ACTIVO")).all()
            if v.producto.estado == "ACTIVO" and any(i.stock_disponible > 0 and i.sucursal.estado == "ACTIVA" for i in v.inventarios)]


def variant_record(db, v):
    category = v.producto.categoria.nombre.lower()
    garment = "pants" if "pantal" in category else "top" if any(word in category for word in ("camis", "chaquet", "poler", "blusa")) else None
    return dict(id_variante=v.id_variante, id_producto=v.id_producto, nombre=v.producto.nombre,
                categoria=v.producto.categoria.nombre, talla=v.talla.nombre, color=v.color.nombre,
                precio=current_price(db, v.producto), garment=garment)



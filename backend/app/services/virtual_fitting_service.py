from fastapi import HTTPException
from sqlalchemy import select

from app.models.recurso_virtual import RecursoVirtual
from app.services.experience_catalog import available_variants, variant_record


class VirtualFittingService:
    def __init__(self, db):
        self.db = db

    def resources(self):
        return self.db.scalars(select(RecursoVirtual).where(
            RecursoVirtual.estado == "ACTIVO", RecursoVirtual.tipo_recurso == "imagen"
        ).order_by(RecursoVirtual.id)).all()

    def list_variants(self):
        product_ids = {resource.id_producto for resource in self.resources()}
        return [variant_record(self.db, variant) for variant in available_variants(self.db)
                if variant.id_producto in product_ids]

    def get_product(self, product_id):
        variants = [variant_record(self.db, variant) for variant in available_variants(self.db)
                    if variant.id_producto == product_id]
        resources = [r for r in self.resources() if r.id_producto == product_id]
        if not variants or not resources:
            raise HTTPException(404, "Este producto no tiene un recurso visual disponible o está agotado")
        return {"id_producto": product_id, "nombre": variants[0]["nombre"], "variantes": variants,
                "recursos": [dict(id=r.id, tipo_recurso=r.tipo_recurso, url_archivo=r.url_archivo,
                                  estado=r.estado) for r in resources]}

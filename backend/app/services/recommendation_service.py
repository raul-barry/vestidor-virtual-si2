"""Explainable MVP ranking from purchases and actual customer interactions."""
import json
from collections import Counter

from fastapi import HTTPException
from sqlalchemy import select

from app.models.bitacora import Bitacora
from app.models.cliente import Cliente
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.services.experience_catalog import available_variants, variant_record


class RecommendationService:
    def __init__(self, db):
        self.db = db

    def record(self, user_id, kind, product_id, variant_id=None):
        product = self.db.get(Producto, product_id)
        variant = self.db.get(ProductoVariante, variant_id) if variant_id else None
        if not product or product.estado != "ACTIVO":
            raise HTTPException(404, "Producto no disponible")
        if variant_id and (not variant or variant.id_producto != product_id or variant.estado != "ACTIVO"):
            raise HTTPException(422, "La variante no pertenece al producto o está inactiva")
        if kind == "seleccion" and not variant:
            raise HTTPException(422, "Selecciona una variante")
        action = "preferencia:" + json.dumps([kind, product_id, variant_id], separators=(",", ":"))
        # Reuse the existing event log; refreshing a page must not inflate preferences.
        existing = self.db.scalar(select(Bitacora).where(
            Bitacora.id_usuario == user_id, Bitacora.accion == action))
        if not existing:
            self.db.add(Bitacora(id_usuario=user_id, accion=action))
            self.db.commit()

    def recommend(self, user_id, talla="", color="", categoria=""):
        sizes, colors, categories = Counter(), Counter(), Counter()
        sources = set()
        history = self.db.scalars(select(PedidoDetalle).join(Pedido).join(Cliente).where(
            Cliente.id_usuario == user_id,
            Pedido.estado.in_(["CONFIRMADO", "ENTREGADO", "ENVIADO"]))).all()
        for detail in history:
            variant = detail.variante
            sizes[variant.talla.nombre] += 3
            colors[variant.color.nombre] += 3
            categories[variant.producto.categoria.nombre] += 3
            sources.add("compras")

        events = self.db.scalars(select(Bitacora).where(
            Bitacora.id_usuario == user_id, Bitacora.accion.like("preferencia:%")
        ).order_by(Bitacora.nro_bitacora.desc()).limit(200)).all()
        for event in events:
            try:
                kind, product_id, variant_id = json.loads(event.accion[len("preferencia:"):])
            except (ValueError, TypeError):
                continue
            if kind not in ("vista", "seleccion", "favorita"):
                continue
            product = self.db.get(Producto, product_id)
            if not product:
                continue
            categories[product.categoria.nombre] += 5 if kind == "favorita" else 1
            variant = self.db.get(ProductoVariante, variant_id) if variant_id else None
            if variant:
                sizes[variant.talla.nombre] += 2
                colors[variant.color.nombre] += 2
            sources.add({"vista": "productos vistos", "seleccion": "tallas y colores seleccionados",
                         "favorita": "categorías favoritas"}[kind])

        rows = []
        for variant in available_variants(self.db):
            row = variant_record(self.db, variant)
            score = sizes[row["talla"]] + colors[row["color"]] + categories[row["categoria"]]
            reasons = ["Relacionado con tus " + ", ".join(sorted(sources))] if score else []
            # A simple explicit compatibility rule, not invented customer history.
            complementary = (row["garment"] == "pants" and any(
                any(word in cat.lower() for word in ("camis", "poler", "blusa")) for cat in categories
            )) or (row["garment"] == "top" and any("pantal" in cat.lower() for cat in categories))
            if complementary:
                score += 2
                reasons.append("Complementa las categorías que te interesan")
            for field, preference in (("talla", talla), ("color", color), ("categoria", categoria)):
                if preference and row[field].casefold() == preference.casefold():
                    score += 10
                    reasons.append(f"Coincide con {field}")
            row.update(puntuacion=score, motivo="; ".join(reasons) or "Prenda disponible para descubrir")
            rows.append(row)
        rows.sort(key=lambda row: (-row["puntuacion"], row["id_variante"]))
        # Show the best available size/color per product instead of duplicate cards.
        products = {}
        for row in rows:
            products.setdefault(row["id_producto"], row)
        return list(products.values())[:20]

from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from PIL import Image

from app.database.seed import seed_roles
from app.main import app
from app.models.categoria import Categoria
from app.models.color import Color
from app.models.inventario import Inventario
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.recurso_virtual import RecursoVirtual
from app.models.sucursal import Sucursal
from app.models.talla import Talla


def image_bytes(color: str = "#d6b09c") -> bytes:
    output = BytesIO()
    Image.new("RGB", (120, 180), color).save(output, format="PNG")
    return output.getvalue()


def auth(client: TestClient) -> dict[str, str]:
    client.post("/api/auth/register", json={
        "nombres": "Ana", "apellidos": "Cliente", "correo": "tryon@example.com",
        "telefono": "70000000", "password": "password-seguro",
    })
    token = client.post("/api/auth/login", json={"correo": "tryon@example.com", "password": "password-seguro"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def product_with_raster(db) -> tuple[int, int, Path]:
    product = Producto(categoria=Categoria(nombre="Camisas", descripcion=None), nombre="Camisa foto", descripcion=None, precio_base=100)
    variant = ProductoVariante(producto=product, talla=Talla(nombre="M"), color=Color(nombre="Azul"), sku="TRY-ON-M-AZUL")
    db.add_all([product, variant, Inventario(variante=variant, sucursal=Sucursal(nombre="Central", direccion="Centro"), stock_disponible=1)])
    db.flush()
    name = f"test-try-on-{uuid4().hex}.png"
    folder = Path(__file__).resolve().parents[1] / "app" / "assets" / "uploads"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(image_bytes("#183f33"))
    db.add(RecursoVirtual(id_producto=product.id_producto, tipo_recurso="imagen", url_archivo=f"/api/assets/uploads/{name}", estado="ACTIVO"))
    db.commit()
    return product.id_producto, variant.id_variante, path


def test_photo_try_on_requires_valid_photo_and_returns_ephemeral_result(db):
    seed_roles(db)
    db.commit()
    client = TestClient(app)
    headers = auth(client)
    product_id, variant_id, garment = product_with_raster(db)
    try:
        invalid = client.post("/api/experience/virtual-try-on", headers=headers, data={"product_id": product_id}, files={"photo": ("photo.png", b"not-an-image", "image/png")})
        response = client.post("/api/experience/virtual-try-on", headers=headers, data={"product_id": product_id, "variant_id": variant_id}, files={"photo": ("photo.png", image_bytes(), "image/png")})
        assert invalid.status_code == 422
        assert response.status_code == 200
        body = response.json()
        assert body["id_producto"] == product_id
        assert body["id_variante"] == variant_id
        assert body["mime_type"] == "image/png"
        # Only the catalogue garment exists on disk; the customer photo/output are response bytes.
        assert garment.exists()
    finally:
        garment.unlink(missing_ok=True)


def test_photo_try_on_rejects_svg_only_catalogue_resource(db):
    seed_roles(db)
    db.commit()
    client = TestClient(app)
    headers = auth(client)
    product = Producto(categoria=Categoria(nombre="Chaquetas", descripcion=None), nombre="Prenda SVG", descripcion=None, precio_base=100)
    variant = ProductoVariante(producto=product, talla=Talla(nombre="M"), color=Color(nombre="Verde"), sku="TRY-ON-SVG-M-VER")
    db.add_all([product, variant, Inventario(variante=variant, sucursal=Sucursal(nombre="Central SVG", direccion="Centro"), stock_disponible=1)])
    db.flush()
    db.add(RecursoVirtual(
        id_producto=product.id_producto,
        tipo_recurso="imagen",
        url_archivo="/api/assets/fitting/prenda-5.svg",
        estado="ACTIVO",
    ))
    db.commit()

    response = client.post(
        "/api/experience/virtual-try-on",
        headers=headers,
        data={"product_id": product.id_producto, "variant_id": variant.id_variante},
        files={"photo": ("photo.png", image_bytes(), "image/png")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "No existe una imagen compatible con el vestidor virtual."

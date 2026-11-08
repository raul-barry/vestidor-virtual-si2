from fastapi.testclient import TestClient

from app.main import app
from app.models.categoria import Categoria
from app.models.organizacion import Organizacion
from app.models.producto import Producto
from app.models.rol import Rol
from app.models.sucursal import Sucursal
from app.models.usuario import Usuario
from conftest import session_token


def test_tenant_users_cannot_read_each_others_catalog_or_admin_lists(db):
    """Exercise tenant isolation over real HTTP routes using the isolated test DB."""
    # Seed both tenants and fixtures outside a tenant context; request auth then
    # establishes the context from each user's persisted organization.
    db.info.pop("organization_id", None)
    organization_a = db.get(Organizacion, 1)
    organization_b = Organizacion(
        id_organizacion=2, nombre="UrbanVogue", slug="urbanvogue", estado="ACTIVA"
    )
    role = Rol(nombre="ADMINISTRADOR", estado="ACTIVO")
    category = Categoria(nombre="Ropa", descripcion="Categoría de prueba")
    db.add_all([organization_b, role, category])
    db.flush()

    branch_a = Sucursal(
        id_organizacion=organization_a.id_organizacion,
        nombre="Sucursal A", direccion="Calle A", estado="ACTIVA",
    )
    branch_b = Sucursal(
        id_organizacion=organization_b.id_organizacion,
        nombre="Sucursal B", direccion="Calle B", estado="ACTIVA",
    )
    product_a = Producto(
        id_organizacion=organization_a.id_organizacion,
        id_categoria=category.id_categoria, nombre="Producto A", precio_base=10, estado="ACTIVO",
    )
    product_b = Producto(
        id_organizacion=organization_b.id_organizacion,
        id_categoria=category.id_categoria, nombre="Producto B", precio_base=20, estado="ACTIVO",
    )
    user_a = Usuario(
        id_organizacion=organization_a.id_organizacion, id_rol=role.id_rol,
        nombres="Admin", apellidos="A", correo="tenant-a@example.test",
        password_hash="test-hash", estado="ACTIVO",
    )
    user_b = Usuario(
        id_organizacion=organization_b.id_organizacion, id_rol=role.id_rol,
        nombres="Admin", apellidos="B", correo="tenant-b@example.test",
        password_hash="test-hash", estado="ACTIVO",
    )
    db.add_all([branch_a, branch_b, product_a, product_b, user_a, user_b])
    db.commit()

    product_a_id, product_b_id = product_a.id_producto, product_b.id_producto
    token_a = session_token(db, {"id_usuario": user_a.id_usuario, "rol": "ADMINISTRADOR"})
    token_b = session_token(db, {"id_usuario": user_b.id_usuario, "rol": "ADMINISTRADOR"})
    client = TestClient(app)
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # A and B can query their own catalog; requesting the other tenant's slug
    # with an authenticated session is rejected instead of switching context.
    own_catalog_a = client.get("/api/catalog/products", headers=headers_a)
    cross_catalog_a = client.get(
        "/api/catalog/products", params={"organization_slug": "urbanvogue"}, headers=headers_a
    )
    own_catalog_b = client.get("/api/catalog/products", headers=headers_b)
    cross_catalog_b = client.get(
        "/api/catalog/products", params={"organization_slug": "fashionstore"}, headers=headers_b
    )
    assert own_catalog_a.status_code == own_catalog_b.status_code == 200
    assert {row["nombre"] for row in own_catalog_a.json()} == {"Producto A"}
    assert {row["nombre"] for row in own_catalog_b.json()} == {"Producto B"}
    assert cross_catalog_a.status_code == cross_catalog_b.status_code == 403

    # Direct lookups do not disclose whether a foreign product exists.
    for headers, own_id, foreign_id in (
        (headers_a, product_a_id, product_b_id),
        (headers_b, product_b_id, product_a_id),
    ):
        own_variants = client.get(f"/api/catalog/products/{own_id}/variants", headers=headers)
        foreign_variants = client.get(f"/api/catalog/products/{foreign_id}/variants", headers=headers)
        foreign_availability = client.get(f"/api/catalog/products/{foreign_id}/availability", headers=headers)
        assert own_variants.status_code == 200
        assert foreign_variants.status_code == 404
        assert foreign_availability.status_code == 404

    # Administrative list routes must be scoped as well, not merely protected
    # against cross-tenant item lookups.
    for headers, own_product, own_branch in (
        (headers_a, "Producto A", "Sucursal A"),
        (headers_b, "Producto B", "Sucursal B"),
    ):
        products = client.get("/api/admin/products", headers=headers)
        branches = client.get("/api/admin/branches", headers=headers)
        assert products.status_code == branches.status_code == 200
        assert {row["nombre"] for row in products.json()} == {own_product}
        assert {row["nombre"] for row in branches.json()} == {own_branch}

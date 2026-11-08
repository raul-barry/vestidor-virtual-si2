from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.tenancy import set_organization_context
from app.database.seed import seed_initial_data
from app.main import app
from app.models.cliente import Cliente
from app.models.loyalty import LoyaltyAccount, LoyaltyLedger, LoyaltyProgram
from app.models.organizacion import Organizacion
from app.models.pedido_detalle import PedidoDetalle
from app.models.plan import Plan, PlanCaracteristica
from app.models.rol import Rol
from app.models.suscripcion import Suscripcion
from app.models.usuario import Usuario
from app.services.loyalty_service import LoyaltyService


def _headers(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"correo": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _seed(db):
    seed_initial_data(db)
    db.commit()


def test_confirmed_pos_sale_accrues_idempotently_and_return_reverses_points(db):
    _seed(db)
    client = TestClient(app)
    admin = _headers(client, "admin@vestidor.local", "Admin123!")
    cashier = _headers(client, "cajero@vestidor.local", "Cajero123!")
    customer = _headers(client, "cliente@vestidor.local", "Cliente123!")
    configured = client.put("/api/loyalty/program", headers=admin, json={
        "active": True, "name": "Club Fashion", "points_per_currency": 1,
        "currency_per_point": 0.01, "minimum_redeem_points": 10,
        "max_discount_percent": 20, "expiration_days": None,
    })
    assert configured.status_code == 200, configured.text
    options = client.get("/api/commerce/pos/options", headers=cashier).json()
    inventory = next(row for row in options["inventario"] if row["stock"] > 0)
    sale = client.post("/api/commerce/pos", headers=cashier, json={
        "id_cliente": options["clientes"][0]["id_cliente"], "metodo_pago": "EFECTIVO",
        "items": [{"id_inventario": inventory["id_inventario"], "cantidad": 1}],
    })
    assert sale.status_code == 201, sale.text
    order_id = sale.json()["id_pedido"]
    balance = client.get("/api/loyalty/me", headers=customer)
    assert balance.status_code == 200, balance.text
    earned = balance.json()["balance"]
    assert earned == int(Decimal(str(sale.json()["total"])))
    assert len([item for item in balance.json()["movements"] if item["kind"] == "ACUMULACION"]) == 1

    assert LoyaltyService(db, 1).accrue_for_order(order_id) == 0
    assert db.scalar(select(LoyaltyAccount).where(LoyaltyAccount.organization_id == 1)).balance == earned

    redemption = client.post("/api/commerce/pos", headers=cashier, json={
        "id_cliente": options["clientes"][0]["id_cliente"], "metodo_pago": "EFECTIVO",
        "puntos_a_canjear": 50,
        "items": [{"id_inventario": inventory["id_inventario"], "cantidad": 1}],
    })
    assert redemption.status_code == 201, redemption.text
    assert redemption.json()["puntos_canjeados"] == 50
    assert Decimal(redemption.json()["descuento_puntos"]) == Decimal("0.50")
    balance_after_redemption = client.get("/api/loyalty/me", headers=customer).json()["balance"]
    assert any(item["kind"] == "CANJE" and item["points"] == -50
               for item in client.get("/api/loyalty/me", headers=customer).json()["movements"])

    detail = db.scalar(select(PedidoDetalle).where(PedidoDetalle.id_pedido == order_id))
    returned = client.post("/api/commerce/returns", headers=admin, json={
        "id_detalle": detail.id_detalle, "id_inventario": inventory["id_inventario"],
        "cantidad": 1, "motivo": "Prueba de reversión de fidelidad",
    })
    assert returned.status_code == 201, returned.text
    after_return = client.get("/api/loyalty/me", headers=customer).json()
    assert after_return["balance"] == balance_after_redemption - earned
    assert any(item["kind"] == "REVERSO" and item["points"] == -earned for item in after_return["movements"])
    assert LoyaltyService(db, 1).reverse_for_return(returned.json()["id_devolucion"]) == 0


def test_loyalty_is_tenant_scoped_and_plan_feature_is_required(db):
    _seed(db)
    role = db.scalar(select(Rol).where(Rol.nombre == "CLIENTE"))
    db.info.pop("organization_id", None)
    other = Organizacion(nombre="Otra tienda", slug="otra-tienda", estado="ACTIVA")
    db.add(other)
    db.flush()
    user = Usuario(id_organizacion=other.id_organizacion, id_rol=role.id_rol,
                   nombres="Cliente", apellidos="Otro", correo="otro@tenant.test", password_hash="hash", estado="ACTIVO")
    db.add(user)
    db.flush()
    other_client = Cliente(id_usuario=user.id_usuario, estado="ACTIVO")
    db.add(other_client)
    plan = db.scalar(select(Plan).limit(1))
    db.add(Suscripcion(organizacion_id=other.id_organizacion, plan_id=plan.id_plan,
                       estado="ACTIVA", fecha_inicio=datetime.now(timezone.utc)))
    db.add(PlanCaracteristica(plan_id=plan.id_plan, codigo="fidelizacion_clientes",
                              nombre="Fidelización de clientes", habilitada=False))
    db.commit()

    set_organization_context(db, 1)
    with pytest.raises(HTTPException) as exc:
        LoyaltyService(db, 1)._account(other_client.id_cliente)
    assert exc.value.status_code == 404
    set_organization_context(db, other.id_organizacion)
    with pytest.raises(HTTPException) as exc:
        LoyaltyService(db).require_feature()
    assert exc.value.status_code == 403


def test_expired_points_are_removed_once_when_customer_checks_balance(db):
    _seed(db)
    customer = db.scalar(select(Cliente).join(Usuario).where(Usuario.correo == "cliente@vestidor.local"))
    account = LoyaltyAccount(organization_id=1, customer_id=customer.id_cliente,
                             balance=40, earned_total=40)
    db.add(account)
    db.flush()
    db.add(LoyaltyProgram(organization_id=1, active=True, name="Club", points_per_currency=1,
                          currency_per_point=Decimal("0.01"), minimum_redeem_points=1,
                          max_discount_percent=20, expiration_days=30,
                          updated_at=datetime.now(timezone.utc)))
    db.add(LoyaltyLedger(organization_id=1, account_id=account.id, event_key="earn:old",
                         kind="ACUMULACION", points=40, amount=Decimal("40"),
                         expires_at=datetime.now(timezone.utc) - timedelta(days=1)))
    db.commit()

    service = LoyaltyService(db, 1)
    assert service.snapshot(customer.id_cliente)["balance"] == 0
    assert service.snapshot(customer.id_cliente)["balance"] == 0
    assert db.scalar(select(LoyaltyAccount).where(LoyaltyAccount.id == account.id)).expired_total == 40
    expirations = db.scalars(select(LoyaltyLedger).where(
        LoyaltyLedger.organization_id == 1, LoyaltyLedger.kind == "EXPIRACION")).all()
    assert len(expirations) == 1

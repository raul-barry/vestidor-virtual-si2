from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.database.database import get_db
from app.models.cliente import Cliente
from app.models.loyalty import LoyaltyProgram, LoyaltyTier
from app.models.usuario import Usuario
from app.services.loyalty_service import LoyaltyService

loyalty_router = APIRouter(prefix="/loyalty", tags=["Fidelización"])


class ProgramUpdate(BaseModel):
    active: bool
    name: str = Field(min_length=1, max_length=120)
    points_per_currency: Decimal = Field(gt=0, le=1000)
    currency_per_point: Decimal = Field(gt=0, le=100)
    minimum_redeem_points: int = Field(ge=0, le=1000000)
    max_discount_percent: Decimal = Field(ge=0, le=100)
    expiration_days: int | None = Field(default=None, gt=0, le=3650)


class TierItem(BaseModel):
    code: str = Field(pattern=r"^[A-Z0-9_-]{1,40}$")
    name: str = Field(min_length=1, max_length=80)
    minimum_points: int = Field(ge=0)


class TierUpdate(BaseModel):
    tiers: list[TierItem] = Field(max_length=10)


class EstimateRequest(BaseModel):
    amount: Decimal = Field(gt=0, le=99999999)
    points: int = Field(gt=0)


class PosEstimateRequest(EstimateRequest):
    customer_id: int = Field(gt=0)


def _customer_id(db: Session, user: Usuario) -> int:
    row = db.scalar(select(Cliente).where(Cliente.id_usuario == user.id_usuario))
    if row is None:
        raise HTTPException(404, "El usuario no tiene perfil de cliente.")
    return row.id_cliente


@loyalty_router.get("/program")
def get_program(db: Session = Depends(get_db), user: Usuario = Depends(require_roles("ADMINISTRADOR"))):
    service = LoyaltyService(db)
    service.require_feature()
    row = service.program()
    tiers = db.scalars(select(LoyaltyTier).where(LoyaltyTier.organization_id == service.organization_id)
                       .order_by(LoyaltyTier.minimum_points)).all()
    return {"program": service.program_dict(row) if row else None,
            "tiers": [{"code": x.code, "name": x.name, "minimum_points": x.minimum_points} for x in tiers]}


@loyalty_router.put("/program")
def update_program(data: ProgramUpdate, db: Session = Depends(get_db), user: Usuario = Depends(require_roles("ADMINISTRADOR"))):
    service = LoyaltyService(db)
    row = service.configure(data.model_dump(), user)
    db.commit()
    return service.program_dict(row)


@loyalty_router.put("/tiers")
def update_tiers(data: TierUpdate, db: Session = Depends(get_db), user: Usuario = Depends(require_roles("ADMINISTRADOR"))):
    service = LoyaltyService(db)
    rows = service.save_tiers([item.model_dump() for item in data.tiers], user)
    db.commit()
    return [{"code": x.code, "name": x.name, "minimum_points": x.minimum_points} for x in rows]


@loyalty_router.get("/me")
def my_loyalty(db: Session = Depends(get_db), user: Usuario = Depends(require_roles("CLIENTE"))):
    return LoyaltyService(db).snapshot(_customer_id(db, user))


@loyalty_router.post("/estimate")
def estimate(data: EstimateRequest, db: Session = Depends(get_db), user: Usuario = Depends(require_roles("CLIENTE"))):
    return LoyaltyService(db).estimate_redemption(_customer_id(db, user), data.amount, data.points)


@loyalty_router.get("/admin/summary")
def summary(db: Session = Depends(get_db), user: Usuario = Depends(require_roles("ADMINISTRADOR"))):
    return LoyaltyService(db).admin_summary()


@loyalty_router.post("/pos/estimate")
def pos_estimate(data: PosEstimateRequest, db: Session = Depends(get_db),
                 user: Usuario = Depends(require_roles("ADMINISTRADOR", "CAJERO"))):
    return LoyaltyService(db).estimate_redemption(data.customer_id, data.amount, data.points)


@loyalty_router.get("/pos/customer/{customer_id}")
def pos_customer(customer_id: int, db: Session = Depends(get_db),
                 user: Usuario = Depends(require_roles("ADMINISTRADOR", "CAJERO"))):
    service = LoyaltyService(db)
    service.require_feature()
    account = service._account(customer_id)
    return {"customer_id": customer_id, "balance": account.balance if account else 0}


@loyalty_router.get("/pos/status")
def pos_status(db: Session = Depends(get_db), user: Usuario = Depends(require_roles("ADMINISTRADOR", "CAJERO"))):
    try:
        service = LoyaltyService(db)
        service.require_feature()
    except HTTPException as exc:
        if exc.status_code == 403:
            return {"enabled": False}
        raise
    program = service.program()
    return {"enabled": bool(program and program.active),
            "minimum_redeem_points": program.minimum_redeem_points if program else None}

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.database.database import get_db
from app.models.perfil_corporal import PerfilCorporal
from app.models.usuario import Usuario

body_profile_router = APIRouter(prefix="/body-profile", tags=["Perfil corporal"])

class BodyProfileRequest(BaseModel):
    consentimiento: bool
    altura_cm: float | None = Field(default=None, gt=0, le=300)
    peso_kg: float | None = Field(default=None, gt=0, le=500)
    pecho_cm: float | None = Field(default=None, gt=0, le=300)
    cintura_cm: float | None = Field(default=None, gt=0, le=300)
    cadera_cm: float | None = Field(default=None, gt=0, le=300)
    largo_pierna_cm: float | None = Field(default=None, gt=0, le=200)
    ancho_hombros_cm: float | None = Field(default=None, gt=0, le=150)

@body_profile_router.get("")
def get_profile(db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    profile = db.query(PerfilCorporal).filter_by(id_usuario=user.id_usuario).one_or_none()
    if not profile:
        raise HTTPException(404, "Perfil corporal no creado")
    return {column.name: getattr(profile, column.name) for column in profile.__table__.columns if not column.name.startswith("foto_")}

@body_profile_router.put("")
def save_profile(data: BodyProfileRequest, db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    if not data.consentimiento:
        raise HTTPException(422, "Se requiere consentimiento explícito para guardar el perfil corporal")
    profile = db.query(PerfilCorporal).filter_by(id_usuario=user.id_usuario).one_or_none()
    if profile is None:
        profile = PerfilCorporal(id_usuario=user.id_usuario, **data.model_dump())
        db.add(profile)
    else:
        for field, value in data.model_dump().items(): setattr(profile, field, value)
    db.commit(); db.refresh(profile)
    return {column.name: getattr(profile, column.name) for column in profile.__table__.columns if not column.name.startswith("foto_")}

@body_profile_router.delete("", status_code=204)
def delete_profile(db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    profile = db.query(PerfilCorporal).filter_by(id_usuario=user.id_usuario).one_or_none()
    if profile: db.delete(profile); db.commit()

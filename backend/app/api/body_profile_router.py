from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.database.database import get_db
from app.models.perfil_corporal import PerfilCorporal
from app.models.usuario import Usuario
from app.services.private_body_image_storage import PrivateBodyImageStorage

body_profile_router = APIRouter(prefix="/body-profile", tags=["Perfil corporal"])
storage = PrivateBodyImageStorage()
photo_fields={"frontal":"foto_frontal","posterior":"foto_posterior","lateral_izquierda":"foto_lateral_izquierda","lateral_derecha":"foto_lateral_derecha"}

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
    if profile:
        for field in photo_fields.values(): storage.delete(getattr(profile,field))
        db.delete(profile); db.commit()

@body_profile_router.put("/photos/{position}")
async def upload_photo(position:str, file:UploadFile=File(...), db:Session=Depends(get_db), user:Usuario=Depends(get_current_user)):
    field=photo_fields.get(position); profile=db.query(PerfilCorporal).filter_by(id_usuario=user.id_usuario).one_or_none()
    if not field or not profile: raise HTTPException(404,"Perfil corporal o posición no encontrada")
    if not profile.consentimiento: raise HTTPException(422,"Se requiere consentimiento activo")
    content=await file.read()
    try: name=storage.save(user.id_usuario,position,content,file.content_type or "")
    except ValueError as error: raise HTTPException(422,str(error))
    storage.delete(getattr(profile,field)); setattr(profile,field,name); db.commit(); return {"position":position,"uploaded":True}

@body_profile_router.get("/photos/{position}")
def get_photo(position:str, db:Session=Depends(get_db), user:Usuario=Depends(get_current_user)):
    field=photo_fields.get(position); profile=db.query(PerfilCorporal).filter_by(id_usuario=user.id_usuario).one_or_none()
    if not field or not profile or not getattr(profile,field): raise HTTPException(404,"Fotografía no encontrada")
    path=storage.path(getattr(profile,field))
    if not path.is_file(): raise HTTPException(404,"Fotografía no encontrada")
    return FileResponse(path)

@body_profile_router.delete("/photos/{position}",status_code=204)
def delete_photo(position:str, db:Session=Depends(get_db), user:Usuario=Depends(get_current_user)):
    field=photo_fields.get(position); profile=db.query(PerfilCorporal).filter_by(id_usuario=user.id_usuario).one_or_none()
    if not field or not profile: raise HTTPException(404,"Perfil corporal o posición no encontrada")
    storage.delete(getattr(profile,field)); setattr(profile,field,None); db.commit()

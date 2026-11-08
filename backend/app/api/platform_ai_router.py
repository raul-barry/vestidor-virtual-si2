from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_platform_admin
from app.database.database import get_db
from app.models.platform_ai_config import PlatformAIConfig, PlatformAIConfigAudit
from app.models.usuario import Usuario
from app.schemas.platform_ai import (
    PlatformAIConfigResponse,
    PlatformAIConfigUpdate,
    PlatformAIConnectionRequest,
    PlatformAIModelResponse,
    PlatformAIModelsRequest,
)
from app.services.ai_provider_service import (
    AIProviderError,
    AIProviderService,
    CAPABILITY_MODELS,
    DEFAULT_MODELS,
    GENERATION_CAPABILITIES,
    encrypt_api_key,
    public_config,
)


platform_ai_router = APIRouter(prefix="/platform/ai", tags=["Administración de IA de plataforma"])


def _get_or_create(db: Session) -> PlatformAIConfig:
    config = db.scalar(select(PlatformAIConfig).where(PlatformAIConfig.id == 1).with_for_update())
    if config is None:
        config = PlatformAIConfig(id=1, models=dict(DEFAULT_MODELS))
        db.add(config)
        db.flush()
    return config


def _audit(db: Session, actor: Usuario, action: str, result: str, models: dict) -> None:
    model_ids = {k: v for k, v in models.items() if k in DEFAULT_MODELS}
    assignments = models.get("capability_models")
    if isinstance(assignments, dict):
        model_ids.update({k: v for k, v in assignments.items() if k in CAPABILITY_MODELS})
    db.add(PlatformAIConfigAudit(
        actor_id=actor.id_usuario, action=action, result=result,
        model_ids=model_ids,
    ))


@platform_ai_router.get("/config", response_model=PlatformAIConfigResponse)
def read_config(db: Session = Depends(get_db), _: Usuario = Depends(get_current_platform_admin)):
    config = db.scalar(select(PlatformAIConfig).where(PlatformAIConfig.id == 1))
    return public_config(config)


@platform_ai_router.post("/models", response_model=list[PlatformAIModelResponse])
def list_models(
    request: PlatformAIModelsRequest,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_platform_admin),
):
    try:
        return AIProviderService(db).list_models(
            request.api_key.get_secret_value() if request.api_key else None
        )
    except AIProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@platform_ai_router.put("/config", response_model=PlatformAIConfigResponse)
def save_config(
    request: PlatformAIConfigUpdate,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(get_current_platform_admin),
):
    values = {
        "primary_model": request.primary_model,
        "fast_model": request.fast_model,
        "vision_model": request.vision_model,
        "transcription_model": request.transcription_model,
        "capability_models": request.capability_models or {
            "general_chat": request.fast_model,
            "complex_reasoning": request.primary_model,
            "business_reports": request.primary_model,
            "sales_analysis": request.primary_model,
            "recommendations": request.primary_model,
            "uml_assistant": request.primary_model,
            "image_understanding": request.vision_model,
            "speech_transcription": request.transcription_model,
        },
    }
    effective_model = settings.groq_model.strip() or "openai/gpt-oss-120b"
    values["primary_model"] = effective_model
    values["fast_model"] = effective_model
    for capability in GENERATION_CAPABILITIES:
        values["capability_models"][capability] = effective_model
    capability_models = values["capability_models"]
    if not isinstance(capability_models, dict) or set(capability_models) != set(CAPABILITY_MODELS):
        raise HTTPException(status_code=422, detail="La asignación debe incluir exactamente las ocho capacidades registradas.")
    config = db.scalar(select(PlatformAIConfig).where(PlatformAIConfig.id == 1).with_for_update())
    candidate_key = request.api_key.get_secret_value() if request.api_key else None
    if candidate_key is None and not request.clear_api_key and config and config.encrypted_api_key:
        try:
            candidate_key = AIProviderService(db)._api_key()
        except AIProviderError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    try:
        if candidate_key is None:
            candidate_key = AIProviderService(db)._api_key()
        AIProviderService(db).validate_models(candidate_key, values, capability_models)
        encrypted_key = encrypt_api_key(candidate_key) if request.api_key else None
    except AIProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    config = config or PlatformAIConfig(id=1)
    if request.api_key:
            config.encrypted_api_key = encrypted_key
    elif request.clear_api_key:
        config.encrypted_api_key = None
    config.models = values
    config.updated_at = datetime.now(timezone.utc)
    db.add(config)
    db.flush()
    _audit(db, actor, "CONFIGURACION_GROQ_GUARDADA", "EXITOSO", values)
    db.commit()
    db.refresh(config)
    return public_config(config)


@platform_ai_router.post("/test")
def test_connection(
    request: PlatformAIConnectionRequest,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(get_current_platform_admin),
):
    config = _get_or_create(db)
    models = dict(config.models or DEFAULT_MODELS)
    candidate_key = request.api_key.get_secret_value() if request.api_key else None
    try:
        if request.capability not in CAPABILITY_MODELS:
            raise AIProviderError("La capacidad solicitada no está registrada.")
        AIProviderService(db).test_connection(
            candidate_key, request.model or (config.models or {}).get("capability_models", {}).get(request.capability)
            or CAPABILITY_MODELS[request.capability], capability=request.capability
        )
    except AIProviderError as exc:
        config.last_test_status = "ERROR"
        config.last_test_at = datetime.now(timezone.utc)
        _audit(db, actor, "PRUEBA_CONEXION_GROQ", "ERROR", models)
        db.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    config.last_test_status = "EXITOSO"
    config.last_test_at = datetime.now(timezone.utc)
    _audit(db, actor, "PRUEBA_CONEXION_GROQ", "EXITOSO", models)
    db.commit()
    return {"ok": True, "message": "Conexión verificada con Groq.", "tested_at": config.last_test_at.isoformat()}

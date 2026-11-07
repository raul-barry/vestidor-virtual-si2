from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from pydantic import SecretStr
from fastapi.testclient import TestClient
from sqlalchemy import select

from conftest import session_token
from app.core.config import settings
from app.main import app
from app.models.platform_ai_config import PlatformAIConfig, PlatformAIConfigAudit
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.services.ai_provider_service import (
    AIProviderError, AIProviderService, CAPABILITY_MODELS, DEFAULT_MODELS, encrypt_api_key, public_config,
)


def _headers(db, role: str, email: str) -> dict[str, str]:
    db.info.pop("organization_id", None)
    row = db.scalar(select(Rol).where(Rol.nombre == role))
    if row is None:
        row = Rol(nombre=role, estado="ACTIVO")
        db.add(row)
        db.flush()
    user = Usuario(
        id_organizacion=None if role == "ADMINISTRADOR_PLATAFORMA" else 1,
        id_rol=row.id_rol, nombres="Prueba", apellidos="IA", correo=email,
        password_hash="unused", estado="ACTIVO",
    )
    db.add(user)
    db.commit()
    token = session_token(db, {"id_usuario": user.id_usuario, "rol": role})
    return {"Authorization": f"Bearer {token}"}


def test_api_key_is_encrypted_and_never_returned(monkeypatch):
    monkeypatch.setattr(settings, "ai_config_encryption_key", SecretStr(Fernet.generate_key().decode("ascii")))
    secret = "gsk_test_secret_value_1234"
    encrypted = encrypt_api_key(secret)
    config = PlatformAIConfig(id=1, encrypted_api_key=encrypted, models=dict(DEFAULT_MODELS))
    rendered = public_config(config)
    assert encrypted != secret
    assert rendered["configured"] is True
    assert rendered["masked_api_key"].endswith("1234")
    assert secret not in repr(rendered)


def test_missing_encryption_master_key_fails_closed(monkeypatch):
    monkeypatch.setattr(settings, "ai_config_encryption_key", SecretStr(""))
    try:
        encrypt_api_key("gsk_test_value")
        assert False, "Expected fail-closed error"
    except AIProviderError as error:
        assert "AI_CONFIG_ENCRYPTION_KEY" in str(error)


def test_groq_environment_key_is_fallback_and_database_key_has_priority(monkeypatch):
    master = Fernet.generate_key().decode("ascii")
    monkeypatch.setattr(settings, "ai_config_encryption_key", SecretStr(master))
    monkeypatch.setattr(settings, "groq_api_key", SecretStr("environment-key"))
    provider = AIProviderService()
    assert provider._api_key() == "environment-key"
    config = PlatformAIConfig(id=1, encrypted_api_key=encrypt_api_key("database-key"), models={})
    provider._config = lambda: config
    assert provider._api_key() == "database-key"


def test_capability_assignment_selects_model_without_falling_back(monkeypatch):
    provider = AIProviderService()
    provider._api_key = lambda override=None: "test-key"
    provider._capability_models = lambda: dict(CAPABILITY_MODELS)
    captured = {}
    monkeypatch.setattr(provider, "_chat", lambda key, model, messages, **kwargs: captured.update(model=model, **kwargs) or "ok")
    response = provider.generate_content({"contents": [{"parts": [{"text": "test"}]}]}, capability="business_reports")
    assert captured["model"] == "openai/gpt-oss-120b"
    assert captured["reasoning_effort"] == "medium"
    assert response["candidates"][0]["content"]["parts"][0]["text"] == "ok"
    try:
        provider.generate_content({"contents": [{"parts": [{"text": "test"}]}]}, capability="nonexistent")
        assert False, "Expected unknown capability to be rejected"
    except AIProviderError as error:
        assert "no está registrada" in str(error)

    provider.generate_content({"contents": [{"parts": [{"text": "pregunta sencilla"}]}]}, capability="general_chat")
    assert captured["model"] == "openai/gpt-oss-20b"
    assert captured["reasoning_effort"] == "low"


def test_transcription_uses_assigned_whisper_and_spanish(monkeypatch):
    captured = {}
    class Response:
        status_code = 200
        def json(self): return {"text": "Analiza las ventas de esta semana."}
    class Client:
        def __init__(self, *, timeout): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, *, headers, data, files):
            captured.update(url=url, data=data, filename=files["file"][0])
            return Response()
    provider = AIProviderService(http_client_factory=Client)
    provider._api_key = lambda override=None: "test-key"
    provider._capability_models = lambda: {**CAPABILITY_MODELS, "speech_transcription": "whisper-test"}
    assert provider.transcribe_audio(b"audio") == "Analiza las ventas de esta semana."
    assert captured["data"] == {"model": "whisper-test", "response_format": "json", "language": "es"}


def test_transient_provider_failure_retries_once():
    state = {"calls": 0}
    class Response:
        def __init__(self, status): self.status_code = status
        def json(self): return {"data": []}
    class Client:
        def __init__(self, *, timeout): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, *args, **kwargs):
            state["calls"] += 1
            return Response(503 if state["calls"] == 1 else 200)
    provider = AIProviderService(http_client_factory=Client)
    provider._api_key = lambda override=None: "test-key"
    assert provider.list_models() == []
    assert state["calls"] == 2


def test_models_are_read_from_groq_and_marked_experimental(monkeypatch):
    monkeypatch.setattr(settings, "ai_config_encryption_key", SecretStr(Fernet.generate_key().decode("ascii")))

    class Response:
        status_code = 200
        def json(self):
            return {"data": [{"id": DEFAULT_MODELS["vision_model"], "active": True},
                             {"id": "llama-test", "active": True}]}

    class Client:
        def __init__(self, *, timeout): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, url, *, headers):
            assert url.endswith("/models")
            assert headers["Authorization"] == "Bearer gsk_temporary"
            return Response()

    result = AIProviderService(http_client_factory=Client).list_models("gsk_temporary")
    assert {row["id"] for row in result} == {DEFAULT_MODELS["vision_model"], "llama-test"}
    assert next(row for row in result if row["id"] == DEFAULT_MODELS["vision_model"])["experimental"] is True


def test_selected_models_must_be_active_and_match_their_capabilities(monkeypatch):
    rows = [
        {"id": "text-model", "active": True, "capabilities": ["text"]},
        {"id": "vision-model", "active": True, "capabilities": ["text", "vision"]},
        {"id": "whisper-model", "active": True, "capabilities": ["transcription"]},
    ]
    monkeypatch.setattr(AIProviderService, "list_models", lambda self, api_key=None: rows)
    provider = AIProviderService()
    provider.validate_models("test-key", {
        "primary_model": "text-model", "fast_model": "text-model",
        "vision_model": "vision-model", "transcription_model": "whisper-model",
    })
    try:
        provider.validate_models("test-key", {
            "primary_model": "text-model", "fast_model": "text-model",
            "vision_model": "whisper-model", "transcription_model": "whisper-model",
        })
        assert False, "Expected an unsupported capability to be rejected"
    except AIProviderError as error:
        assert "no admite" in str(error)


def test_platform_admin_can_save_encrypted_config_but_tenant_admin_cannot(db, monkeypatch):
    monkeypatch.setattr(settings, "ai_config_encryption_key", SecretStr(Fernet.generate_key().decode("ascii")))
    platform_headers = _headers(db, "ADMINISTRADOR_PLATAFORMA", "platform-ai@example.test")
    tenant_headers = _headers(db, "ADMINISTRADOR", "tenant-ai@example.test")
    available = {"test-primary", "test-fast", "test-vision", "test-transcription"}
    monkeypatch.setattr(AIProviderService, "list_models", lambda self, api_key=None: [
        {"id": model, "active": True, "experimental": False,
         "capabilities": ["transcription"] if model == "test-transcription" else
                         ["text", "vision"] if model == "test-vision" else ["text"]}
        for model in available
    ])
    payload = {
        "api_key": "gsk_secret_never_returned",
        "primary_model": "test-primary", "fast_model": "test-fast",
        "vision_model": "test-vision", "transcription_model": "test-transcription",
        "capability_models": {
            "general_chat": "test-fast", "complex_reasoning": "test-primary",
            "business_reports": "test-primary", "sales_analysis": "test-primary",
            "recommendations": "test-primary", "uml_assistant": "test-primary",
            "image_understanding": "test-vision", "speech_transcription": "test-transcription",
        },
    }
    client = TestClient(app)
    denied = client.put("/api/platform/ai/config", headers=tenant_headers, json=payload)
    saved = client.put("/api/platform/ai/config", headers=platform_headers, json=payload)
    loaded = client.get("/api/platform/ai/config", headers=platform_headers)
    assert denied.status_code == 403
    assert saved.status_code == 200, saved.text
    assert saved.json()["configured"] is True
    assert "gsk_secret_never_returned" not in saved.text
    assert "gsk_secret_never_returned" not in loaded.text
    row = db.scalar(select(PlatformAIConfig).where(PlatformAIConfig.id == 1))
    assert row.encrypted_api_key != payload["api_key"]
    assert row.models["capability_models"] == payload["capability_models"]
    audit = db.scalar(select(PlatformAIConfigAudit).where(
        PlatformAIConfigAudit.action == "CONFIGURACION_GROQ_GUARDADA"
    ))
    assert audit is not None and "api_key" not in audit.model_ids


def test_connection_test_is_real_and_updates_status(db, monkeypatch):
    monkeypatch.setattr(settings, "ai_config_encryption_key", SecretStr(Fernet.generate_key().decode("ascii")))
    headers = _headers(db, "ADMINISTRADOR_PLATAFORMA", "platform-ai-test@example.test")
    monkeypatch.setattr(AIProviderService, "list_models", lambda self, api_key=None: [
        {"id": "known-model", "active": True, "experimental": False, "capabilities": ["text"]}
    ])
    called = {}
    def fake_chat(self, key, model, messages, *, timeout, response_format=None, reasoning_effort=None):
        called.update(key=key, model=model, prompt=messages[0]["content"])
        return "conexión correcta"
    monkeypatch.setattr(AIProviderService, "_chat", fake_chat)
    response = TestClient(app).post("/api/platform/ai/test", headers=headers,
                                    json={"api_key": "gsk_test", "model": "known-model"})
    assert response.status_code == 200, response.text
    assert called["model"] == "known-model" and called["key"] == "gsk_test"
    config = db.scalar(select(PlatformAIConfig).where(PlatformAIConfig.id == 1))
    assert config.last_test_status == "EXITOSO" and config.last_test_at is not None

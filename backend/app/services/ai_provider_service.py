"""Platform-configured Groq provider for supported AI workloads."""
from __future__ import annotations

from io import BytesIO
from typing import Any
import wave
import time

import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.platform_ai_config import PlatformAIConfig


DEFAULT_MODELS = {
    "primary_model": "openai/gpt-oss-120b",
    "fast_model": "openai/gpt-oss-20b",
    "vision_model": "qwen/qwen3.8-27b",
    "transcription_model": "whisper-large-v3-turbo",
}
CAPABILITY_MODELS = {
    "general_chat": DEFAULT_MODELS["fast_model"],
    "complex_reasoning": DEFAULT_MODELS["primary_model"],
    "business_reports": DEFAULT_MODELS["primary_model"],
    "sales_analysis": DEFAULT_MODELS["primary_model"],
    "recommendations": DEFAULT_MODELS["primary_model"],
    "uml_assistant": DEFAULT_MODELS["primary_model"],
    "image_understanding": DEFAULT_MODELS["vision_model"],
    "speech_transcription": DEFAULT_MODELS["transcription_model"],
}
EXPERIMENTAL_MODELS = {DEFAULT_MODELS["vision_model"]}
GROQ_API_BASE = "https://api.groq.com/openai/v1"
MAX_TRANSIENT_RETRIES = 1


class AIProviderError(RuntimeError):
    """Safe-to-display provider failure; never contains credentials or response bodies."""


def _cipher() -> Fernet:
    key = settings.ai_config_encryption_key.get_secret_value().strip()
    if not key:
        raise AIProviderError("La clave maestra AI_CONFIG_ENCRYPTION_KEY no está configurada en el servidor.")
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise AIProviderError("La clave maestra de cifrado de IA no tiene un formato válido.") from exc


class AIProviderService:
    def __init__(self, db: Session | None = None, *, http_client_factory=None) -> None:
        self.db = db
        self.http_client_factory = http_client_factory or httpx.Client

    def _config(self) -> PlatformAIConfig | None:
        if self.db is None:
            return None
        return self.db.scalar(select(PlatformAIConfig).where(PlatformAIConfig.id == 1))

    def _request(self, method: str, url: str, *, timeout: float, **kwargs) -> httpx.Response:
        for attempt in range(MAX_TRANSIENT_RETRIES + 1):
            try:
                with self.http_client_factory(timeout=timeout) as client:
                    response = getattr(client, method)(url, **kwargs)
            except (httpx.TimeoutException, httpx.ConnectError):
                if attempt >= MAX_TRANSIENT_RETRIES:
                    raise
                time.sleep(0.2)
                continue
            if response.status_code not in {502, 503, 504} or attempt >= MAX_TRANSIENT_RETRIES:
                return response
            time.sleep(0.2)
        raise AIProviderError("No fue posible completar la solicitud a Groq.")

    def _api_key(self, override: str | None = None) -> str:
        if override and override.strip():
            return override.strip()
        config = self._config()
        if config and config.encrypted_api_key:
            try:
                return _cipher().decrypt(config.encrypted_api_key.encode("ascii")).decode("utf-8")
            except (InvalidToken, UnicodeDecodeError, ValueError) as exc:
                raise AIProviderError("No se pudo leer la configuración cifrada de IA.") from exc
        env_key = settings.groq_api_key.get_secret_value().strip()
        if env_key:
            return env_key
        raise AIProviderError("La integración de IA de plataforma no está configurada.")

    def _models(self) -> dict[str, str]:
        config = self._config()
        models = dict(DEFAULT_MODELS)
        if config and isinstance(config.models, dict):
            models.update({k: v for k, v in config.models.items() if k in DEFAULT_MODELS and isinstance(v, str)})
        return models

    def _capability_models(self) -> dict[str, str]:
        aliases = self._models()
        models = {
            "general_chat": aliases["fast_model"],
            "complex_reasoning": aliases["primary_model"],
            "business_reports": aliases["primary_model"],
            "sales_analysis": aliases["primary_model"],
            "recommendations": aliases["primary_model"],
            "uml_assistant": aliases["primary_model"],
            "image_understanding": aliases["vision_model"],
            "speech_transcription": aliases["transcription_model"],
        }
        config = self._config()
        if config and isinstance(config.models, dict):
            selected = config.models.get("capability_models")
            if isinstance(selected, dict):
                models.update({key: value for key, value in selected.items()
                               if key in CAPABILITY_MODELS and isinstance(value, str) and value})
        return models

    def list_models(self, api_key: str | None = None) -> list[dict[str, Any]]:
        key = self._api_key(api_key)
        try:
            response = self._request("get", f"{GROQ_API_BASE}/models", timeout=15.0,
                                     headers={"Authorization": f"Bearer {key}"})
        except httpx.HTTPError as exc:
            raise AIProviderError("No fue posible conectar con Groq.") from exc
        if response.status_code >= 400:
            raise self._http_error(response.status_code)
        try:
            data = response.json()["data"]
            if not isinstance(data, list):
                raise ValueError("Invalid model list")
            rows = [item for item in data if isinstance(item, dict) and isinstance(item.get("id"), str)]
        except (ValueError, TypeError, KeyError) as exc:
            raise AIProviderError("Groq devolvió una lista de modelos inválida.") from exc
        return sorted(
            ({"id": item["id"], "active": item.get("active", True) is not False,
              "experimental": item["id"] in EXPERIMENTAL_MODELS,
              "capabilities": self._capabilities(item["id"])} for item in rows),
            key=lambda item: item["id"],
        )

    @staticmethod
    def _capabilities(model_id: str) -> list[str]:
        capabilities = ["text"]
        if "whisper" in model_id.lower():
            return ["transcription"]
        if model_id in EXPERIMENTAL_MODELS or "vision" in model_id.lower():
            capabilities.append("vision")
        return capabilities

    def validate_models(self, api_key: str, selected: dict[str, str], capability_models: dict[str, str] | None = None) -> None:
        models = {item["id"]: item for item in self.list_models(api_key) if item["active"]}
        assignments = {key: selected[value] for key, value in {
            "general_chat": "fast_model", "complex_reasoning": "primary_model",
            "business_reports": "primary_model", "sales_analysis": "primary_model",
            "recommendations": "primary_model", "uml_assistant": "primary_model",
            "image_understanding": "vision_model", "speech_transcription": "transcription_model",
        }.items()}
        if capability_models is not None:
            assignments.update(capability_models)
        all_selected = {**{key: value for key, value in selected.items() if isinstance(value, str)}, **assignments}
        missing = sorted({model for model in all_selected.values() if model not in models})
        if missing:
            raise AIProviderError("Los siguientes modelos no están disponibles en Groq: " + ", ".join(missing))
        for field, capability in (("primary_model", "text"), ("fast_model", "text"),
                                  ("vision_model", "vision"), ("transcription_model", "transcription")):
            if capability not in models[selected[field]]["capabilities"]:
                raise AIProviderError(f"El modelo seleccionado para {field} no admite la capacidad {capability}.")
        for capability, model_id in assignments.items():
            expected = "vision" if capability == "image_understanding" else (
                "transcription" if capability == "speech_transcription" else "text")
            if expected not in models[model_id]["capabilities"]:
                raise AIProviderError(f"El modelo seleccionado para {capability} no admite la capacidad {expected}.")

    def test_connection(self, api_key: str | None = None, model: str | None = None,
                        capability: str = "complex_reasoning") -> None:
        key = self._api_key(api_key)
        if capability not in CAPABILITY_MODELS:
            raise AIProviderError("La capacidad solicitada no está registrada.")
        model_id = model or self._capability_models()[capability]
        listed = {item["id"]: item for item in self.list_models(key) if item["active"]}
        if model_id not in listed:
            raise AIProviderError("El modelo seleccionado no está disponible en Groq.")
        expected = "vision" if capability == "image_understanding" else (
            "transcription" if capability == "speech_transcription" else "text")
        if expected not in listed[model_id]["capabilities"]:
            raise AIProviderError(f"El modelo seleccionado no admite la capacidad {expected}.")
        if expected == "text":
            self._chat(key, model_id, [{"role": "user", "content": "Responde únicamente: conexión correcta"}],
                       timeout=20.0, reasoning_effort="medium" if model_id.startswith("openai/gpt-oss-") else None)
        elif expected == "vision":
            pixel = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/nWQAAAAASUVORK5CYII="
            self._chat(key, model_id, [{"role": "user", "content": [
                {"type": "text", "text": "Responde únicamente: imagen recibida"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{pixel}"}},
            ]}], timeout=30.0)
        else:
            audio = BytesIO()
            with wave.open(audio, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                wav.writeframes(b"\0\0" * 1600)
            try:
                response = self._request(
                    "post", f"{GROQ_API_BASE}/audio/transcriptions", timeout=30.0,
                    headers={"Authorization": f"Bearer {key}"},
                    data={"model": model_id, "response_format": "json", "language": "es"},
                    files={"file": ("probe.wav", audio.getvalue(), "audio/wav")},
                )
            except httpx.HTTPError as exc:
                raise AIProviderError("No fue posible conectar con el servicio de transcripción de Groq.") from exc
            if response.status_code >= 400:
                raise self._http_error(response.status_code)
            try:
                if not isinstance(response.json().get("text"), str):
                    raise ValueError("invalid transcription payload")
            except (ValueError, TypeError, AttributeError) as exc:
                raise AIProviderError("Groq devolvió una respuesta de transcripción inválida.") from exc

    def generate_content(self, body: dict, *, timeout: float = 90.0, capability: str = "complex_reasoning") -> dict:
        text = "\n".join(
            part["text"] for item in body.get("contents", []) if isinstance(item, dict)
            for part in item.get("parts", []) if isinstance(part, dict) and isinstance(part.get("text"), str)
        )
        if not text:
            raise AIProviderError("No hay contenido para enviar al proveedor de IA.")
        key = self._api_key()
        model = self._capability_models().get(capability)
        if model is None:
            raise AIProviderError("La capacidad de IA solicitada no está registrada.")
        response_format = {"type": "json_object"} if "json" in text.lower() else None
        reasoning_effort = ("low" if capability == "general_chat" else "medium") \
            if model.startswith("openai/gpt-oss-") else None
        payload = self._chat(key, model, [{"role": "user", "content": text}], timeout=timeout,
                             response_format=response_format, reasoning_effort=reasoning_effort)
        return {"candidates": [{"content": {"parts": [{"text": payload}]}}]}

    def analyze_image(self, instruction: str, image_data_url: str, *, allow_experimental: bool = False,
                      timeout: float = 60.0) -> str:
        if not image_data_url.startswith("data:image/"):
            raise AIProviderError("La imagen debe proporcionarse como data URL de imagen.")
        model = self._capability_models()["image_understanding"]
        if model in EXPERIMENTAL_MODELS and not allow_experimental:
            raise AIProviderError("El modelo de visión es experimental y requiere una habilitación explícita.")
        key = self._api_key()
        messages = [{"role": "user", "content": [
            {"type": "text", "text": instruction},
            {"type": "image_url", "image_url": {"url": image_data_url}},
        ]}]
        return self._chat(key, model, messages, timeout=timeout)

    def transcribe_audio(self, audio: bytes, *, filename: str = "audio.wav", mime_type: str = "audio/wav",
                         timeout: float = 90.0, language: str = "es") -> str:
        if not audio:
            raise AIProviderError("El audio está vacío.")
        key = self._api_key()
        model = self._capability_models()["speech_transcription"]
        try:
            response = self._request(
                "post", f"{GROQ_API_BASE}/audio/transcriptions", timeout=timeout,
                headers={"Authorization": f"Bearer {key}"},
                data={"model": model, "response_format": "json", "language": language},
                files={"file": (filename, audio, mime_type)},
            )
        except httpx.HTTPError as exc:
            raise AIProviderError("No fue posible conectar con el servicio de transcripción de Groq.") from exc
        if response.status_code >= 400:
            raise self._http_error(response.status_code)
        try:
            text = response.json()["text"]
        except (ValueError, TypeError, KeyError) as exc:
            raise AIProviderError("Groq devolvió una transcripción inválida.") from exc
        if not isinstance(text, str) or not text.strip():
            raise AIProviderError("Groq devolvió una transcripción vacía.")
        return text.strip()

    def _chat(self, key: str, model: str, messages: list[dict], *, timeout: float,
              response_format: dict | None = None, reasoning_effort: str | None = None) -> str:
        body: dict[str, Any] = {"model": model, "messages": messages, "temperature": 0.2}
        if response_format:
            body["response_format"] = response_format
        if reasoning_effort in {"low", "medium", "high"}:
            body["reasoning_effort"] = reasoning_effort
        try:
            response = self._request(
                "post", f"{GROQ_API_BASE}/chat/completions", timeout=timeout,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json=body,
            )
        except httpx.HTTPError as exc:
            raise AIProviderError("No fue posible conectar con Groq.") from exc
        if response.status_code >= 400:
            raise self._http_error(response.status_code)
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, TypeError, KeyError, IndexError) as exc:
            raise AIProviderError("Groq devolvió una respuesta inválida.") from exc
        if not isinstance(content, str) or not content.strip():
            raise AIProviderError("Groq devolvió una respuesta vacía.")
        return content

    @staticmethod
    def _http_error(status_code: int) -> AIProviderError:
        if status_code == 401 or status_code == 403:
            return AIProviderError("Groq rechazó la API Key o no autorizó la operación.")
        if status_code == 429:
            return AIProviderError("Groq alcanzó el límite de solicitudes; inténtalo más tarde.")
        return AIProviderError(f"Groq rechazó la solicitud ({status_code}).")


def public_config(config: PlatformAIConfig | None) -> dict[str, Any]:
    models = dict(DEFAULT_MODELS)
    if config and isinstance(config.models, dict):
        models.update({k: v for k, v in config.models.items() if k in DEFAULT_MODELS})
    capability_models = {
        "general_chat": models["fast_model"], "complex_reasoning": models["primary_model"],
        "business_reports": models["primary_model"], "sales_analysis": models["primary_model"],
        "recommendations": models["primary_model"], "uml_assistant": models["primary_model"],
        "image_understanding": models["vision_model"], "speech_transcription": models["transcription_model"],
    }
    if config and isinstance(config.models, dict) and isinstance(config.models.get("capability_models"), dict):
        capability_models.update({k: v for k, v in config.models["capability_models"].items()
                                  if k in CAPABILITY_MODELS and isinstance(v, str)})
    encrypted = config.encrypted_api_key if config else None
    masked = None
    if encrypted:
        try:
            key = _cipher().decrypt(encrypted.encode("ascii")).decode("utf-8")
            masked = f"••••••••{key[-4:]}" if len(key) >= 4 else "••••••••"
        except (AIProviderError, InvalidToken, ValueError, UnicodeDecodeError):
            masked = "Configurada"
    return {
        "configured": bool(encrypted) or bool(settings.groq_api_key.get_secret_value().strip()),
        "masked_api_key": masked or ("Configurada por entorno" if settings.groq_api_key.get_secret_value().strip() else None),
        **models, "capability_models": capability_models,
        "experimental_models": sorted(EXPERIMENTAL_MODELS),
        "last_test_status": config.last_test_status if config else None,
        "last_test_at": config.last_test_at.isoformat() if config and config.last_test_at else None,
    }


def encrypt_api_key(value: str) -> str:
    if not value.strip():
        raise AIProviderError("La API Key no puede estar vacía.")
    return _cipher().encrypt(value.strip().encode("utf-8")).decode("ascii")

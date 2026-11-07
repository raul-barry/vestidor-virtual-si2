"""Shared HTTP client for the virtual try-on Gemini integration."""
from __future__ import annotations

import httpx

from app.core.config import settings


class GeminiClientError(RuntimeError):
    pass


class GeminiClient:
    _endpoint = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def generate_content(self, body: dict, *, timeout: float = 90.0) -> dict:
        if not settings.gemini_api_key.strip():
            raise GeminiClientError("La integración Gemini no está configurada.")
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    self._endpoint.format(model=settings.gemini_model),
                    headers={"x-goog-api-key": settings.gemini_api_key}, json=body,
                )
        except httpx.HTTPError as exc:
            raise GeminiClientError("No fue posible conectar con Gemini.") from exc
        if response.status_code >= 400:
            raise GeminiClientError(f"Gemini rechazó la solicitud ({response.status_code}).")
        try:
            payload = response.json()
        except (ValueError, TypeError) as exc:
            raise GeminiClientError("Gemini devolvió una respuesta inválida.") from exc
        if not isinstance(payload, dict):
            raise GeminiClientError("Gemini devolvió una respuesta inválida.")
        return payload

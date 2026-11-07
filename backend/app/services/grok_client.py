"""xAI Grok client for tenant-scoped report recommendations."""
from __future__ import annotations

import httpx

from app.core.config import settings


class GrokClientError(RuntimeError):
    pass


class GrokClient:
    endpoint = "https://api.x.ai/v1/chat/completions"

    def generate_content(self, body: dict, *, timeout: float = 90.0) -> dict:
        api_key = settings.grok_api_key.strip()
        if not api_key:
            raise GrokClientError("La integración Grok no está configurada; define GROK_API_KEY.")
        text = "\n".join(
            part["text"] for item in body.get("contents", []) if isinstance(item, dict)
            for part in item.get("parts", []) if isinstance(part, dict) and isinstance(part.get("text"), str)
        )
        if not text:
            raise GrokClientError("No hay contenido para enviar a Grok.")
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    self.endpoint,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": settings.grok_model,
                          "messages": [{"role": "user", "content": text}],
                          "response_format": {"type": "json_object"}, "temperature": 0.2},
                )
        except httpx.HTTPError as exc:
            raise GrokClientError("No fue posible conectar con Grok.") from exc
        if response.status_code == 429:
            raise GrokClientError("Grok alcanzó el límite de solicitudes; inténtalo más tarde.")
        if response.status_code >= 400:
            raise GrokClientError(f"Grok rechazó la solicitud ({response.status_code}).")
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, TypeError, KeyError, IndexError) as exc:
            raise GrokClientError("Grok devolvió una respuesta inválida.") from exc
        if not isinstance(content, str) or not content.strip():
            raise GrokClientError("Grok devolvió una respuesta vacía.")
        return {"candidates": [{"content": {"parts": [{"text": content}]}}]}

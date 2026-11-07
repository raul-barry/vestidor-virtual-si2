import json

import pytest

from app.core.config import settings
from app.services.grok_client import GrokClient, GrokClientError


def test_grok_client_sends_aggregated_prompt_and_normalizes_json_response(monkeypatch):
    captured = {}

    class Response:
        status_code = 200
        def json(self):
            return {"choices": [{"message": {"content": json.dumps({"observaciones": ["Dato"], "recomendaciones": ["Acción"]})}}]}

    class Client:
        def __init__(self, *, timeout): captured["timeout"] = timeout
        def __enter__(self): return self
        def __exit__(self, *args): return None
        def post(self, url, *, headers, json):
            captured.update(url=url, headers=headers, body=json)
            return Response()

    monkeypatch.setattr(settings, "grok_api_key", "test-only-key")
    monkeypatch.setattr(settings, "grok_model", "test-model")
    monkeypatch.setattr("app.services.grok_client.httpx.Client", Client)
    result = GrokClient().generate_content({"contents": [{"parts": [{"text": "tenant metrics"}]}]})
    assert captured["url"] == "https://api.x.ai/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-only-key"
    assert captured["body"]["model"] == "test-model"
    assert captured["body"]["messages"][0]["content"] == "tenant metrics"
    assert json.loads(result["candidates"][0]["content"]["parts"][0]["text"])["observaciones"] == ["Dato"]


def test_grok_client_reports_missing_key_without_network(monkeypatch):
    monkeypatch.setattr(settings, "grok_api_key", "")
    with pytest.raises(GrokClientError, match="GROK_API_KEY"):
        GrokClient().generate_content({"contents": [{"parts": [{"text": "metrics"}]}]})

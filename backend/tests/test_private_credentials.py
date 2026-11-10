import json

import pytest

from app.database import private_credentials
from app.database.private_credentials import (
    CredentialManifestError,
    mark_credentials_active,
    prepare_credentials,
)


def test_private_credentials_are_unique_reusable_and_marked_active(tmp_path, monkeypatch):
    monkeypatch.setattr(private_credentials, "DEFAULT_CREDENTIALS_DIR", tmp_path)
    path = tmp_path / "accounts.json"
    identities = [
        {"name": "Ana Test", "email": "ana@vestidor.com", "role": "CLIENTE",
         "tenant": "Magnolia Boutique", "branch": None},
        {"name": "Luis Test", "email": "luis@vestidor.com", "role": "CAJERO",
         "tenant": "Punto Nativo", "branch": "Centro"},
    ]

    manifest, created = prepare_credentials(path, identities)
    assert created is True
    passwords = [row["initial_password"] for row in manifest["accounts"]]
    assert len(set(passwords)) == 2
    assert all(len(password) >= 20 for password in passwords)
    assert all(row["status"] == "PENDIENTE_APPLY" for row in manifest["accounts"])

    reused, created_again = prepare_credentials(path, identities)
    assert created_again is False
    assert [row["initial_password"] for row in reused["accounts"]] == passwords

    mark_credentials_active(path, reused)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert all(row["status"] == "ACTIVO" for row in saved["accounts"])
    assert [row["initial_password"] for row in saved["accounts"]] == passwords


def test_private_credentials_reject_mismatched_accounts_and_outside_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(private_credentials, "DEFAULT_CREDENTIALS_DIR", tmp_path)
    path = tmp_path / "accounts.json"
    identities = [{"name": "Ana Test", "email": "ana@vestidor.com",
                   "role": "CLIENTE", "tenant": "Magnolia", "branch": None}]
    prepare_credentials(path, identities)

    with pytest.raises(CredentialManifestError, match="no coincide"):
        prepare_credentials(path, [{**identities[0], "tenant": "Punto Nativo"}])
    with pytest.raises(CredentialManifestError, match="backend/private_credentials"):
        prepare_credentials(tmp_path.parent / "outside.json", identities)

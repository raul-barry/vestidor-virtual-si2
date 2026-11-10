from datetime import datetime, timedelta, timezone
import hashlib
import json
from types import SimpleNamespace

import pytest
from sqlalchemy.engine import make_url

from app.database.render_seed_safety import (
    APPROVED_RENDER_DATABASE_NAME,
    APPROVED_RENDER_POSTGRES_ID,
    RenderSeedSafetyError,
    probe_render_connection,
    validate_render_url,
    verify_backup_attestation,
)


def test_render_url_requires_the_allowlisted_resource_and_database():
    internal = make_url(
        f"postgresql://user:secret@{APPROVED_RENDER_POSTGRES_ID}:5432/{APPROVED_RENDER_DATABASE_NAME}"
    )
    external = make_url(
        f"postgresql://user:secret@{APPROVED_RENDER_POSTGRES_ID}.oregon-postgres.render.com/"
        f"{APPROVED_RENDER_DATABASE_NAME}?sslmode=require"
    )

    assert validate_render_url(internal, APPROVED_RENDER_POSTGRES_ID)["connection_kind"] == "internal"
    assert validate_render_url(external, APPROVED_RENDER_POSTGRES_ID)["connection_kind"] == "external"
    with pytest.raises(RenderSeedSafetyError):
        validate_render_url(internal, "dpg-arbitrary")
    with pytest.raises(RenderSeedSafetyError):
        validate_render_url(internal.set(host="other-db.internal"), APPROVED_RENDER_POSTGRES_ID)
    with pytest.raises(RenderSeedSafetyError):
        validate_render_url(internal.set(database="other_db"), APPROVED_RENDER_POSTGRES_ID)
    with pytest.raises(RenderSeedSafetyError):
        validate_render_url(external.set(query={"sslmode": "disable"}), APPROVED_RENDER_POSTGRES_ID)


def test_live_probe_checks_database_name_and_server_major():
    class Connection:
        def __init__(self, row):
            self.row = row

        def exec_driver_sql(self, _sql):
            return SimpleNamespace(one=lambda: self.row)

    result = probe_render_connection(
        Connection((APPROVED_RENDER_DATABASE_NAME, "160004")), APPROVED_RENDER_POSTGRES_ID,
    )
    assert result["postgres_major"] == "16"
    with pytest.raises(RenderSeedSafetyError):
        probe_render_connection(Connection(("wrong_database", "160004")), APPROVED_RENDER_POSTGRES_ID)
    with pytest.raises(RenderSeedSafetyError):
        probe_render_connection(Connection((APPROVED_RENDER_DATABASE_NAME, "170001")), APPROVED_RENDER_POSTGRES_ID)


def test_backup_attestation_checks_resource_freshness_hash_and_archive(monkeypatch, tmp_path):
    import app.database.render_seed_safety as safety

    backup = tmp_path / "vestidor.dump"
    backup.write_bytes(b"synthetic archive bytes")
    digest = hashlib.sha256(backup.read_bytes()).hexdigest()
    created = datetime.now(timezone.utc)
    manifest = tmp_path / "vestidor.dump.manifest.json"
    manifest.write_text(json.dumps({
        "render_postgres_id": APPROVED_RENDER_POSTGRES_ID,
        "database_name": APPROVED_RENDER_DATABASE_NAME,
        "created_at_utc": created.isoformat(),
        "file_name": backup.name,
        "sha256": digest,
        "format": "custom",
    }), encoding="utf-8")
    monkeypatch.setattr(safety.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=0, stdout=f"; Database: {APPROVED_RENDER_DATABASE_NAME}\n", stderr="",
    ))

    checked = verify_backup_attestation(
        backup, manifest, APPROVED_RENDER_POSTGRES_ID,
        now=created + timedelta(minutes=5), pg_restore="pg_restore-test",
    )
    assert checked["sha256"] == digest
    with pytest.raises(RenderSeedSafetyError):
        verify_backup_attestation(
            backup, manifest, APPROVED_RENDER_POSTGRES_ID,
            now=created + timedelta(hours=25), pg_restore="pg_restore-test",
        )
    manifest.write_text(manifest.read_text(encoding="utf-8").replace(digest, "0" * 64), encoding="utf-8")
    with pytest.raises(RenderSeedSafetyError):
        verify_backup_attestation(backup, manifest, APPROVED_RENDER_POSTGRES_ID, pg_restore="pg_restore-test")

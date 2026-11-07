from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditService:
    """Writes safe, transactional audit events and reads scoped activity."""

    @staticmethod
    def record(db: Session, *, organization_id: int, actor_id: int | None, actor_role: str,
               action: str, entity: str, entity_id: int | str | None,
               result: str = "EXITOSO", details: dict | None = None,
               dedupe_key: str | None = None) -> AuditLog:
        # Callers pass only identifiers, state values, and changed field names.
        if dedupe_key:
            existing = db.scalar(select(AuditLog).where(AuditLog.dedupe_key == dedupe_key))
            if existing is not None:
                return existing
        safe_details = {str(k): v for k, v in (details or {}).items()
                        if str(k).lower() not in {"password", "password_hash", "token", "cvv", "card_number", "numero_tarjeta", "correo", "email", "telefono", "nombre", "apellidos"}}
        row = AuditLog(organizacion_id=organization_id, usuario_id=actor_id,
                       rol=actor_role, accion=action, entidad=entity,
                       entidad_id=str(entity_id) if entity_id is not None else None,
                       fecha_hora=datetime.now(timezone.utc), resultado=result,
                       detalles=safe_details, dedupe_key=dedupe_key)
        db.add(row)
        if dedupe_key:
            from sqlalchemy.exc import IntegrityError
            try:
                # The unique index closes the race between concurrent workers.
                with db.begin_nested():
                    db.flush([row])
            except IntegrityError:
                existing = db.scalar(select(AuditLog).where(AuditLog.dedupe_key == dedupe_key))
                if existing is not None:
                    return existing
                raise
        return row

    @staticmethod
    def list_activity(db: Session, organization_id: int, *, desde: datetime | None = None,
                      hasta: datetime | None = None, tipo: str | None = None,
                      usuario_id: int | None = None, limit: int = 25, offset: int = 0):
        filters = [AuditLog.organizacion_id == organization_id]
        if desde is not None: filters.append(AuditLog.fecha_hora >= desde)
        if hasta is not None: filters.append(AuditLog.fecha_hora <= hasta)
        if tipo: filters.append(AuditLog.accion == tipo)
        if usuario_id is not None: filters.append(AuditLog.usuario_id == usuario_id)
        total = db.scalar(select(func.count()).select_from(AuditLog).where(*filters)) or 0
        rows = db.scalars(select(AuditLog).where(*filters).order_by(AuditLog.fecha_hora.desc(), AuditLog.id.desc()).offset(offset).limit(limit)).all()
        return total, rows

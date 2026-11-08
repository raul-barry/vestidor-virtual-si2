from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.loyalty import LoyaltyAccount, LoyaltyLedger, LoyaltyProgram, LoyaltyTier
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.pago import Pago
from app.models.usuario import Usuario
from app.services.audit_service import AuditService
from app.services.plan_access_service import PlanAccessService


class LoyaltyService:
    def __init__(self, db: Session, organization_id: int | None = None):
        self.db = db
        current_scope = db.info.get("organization_id")
        if organization_id is not None and current_scope is not None and organization_id != current_scope:
            raise HTTPException(403, "La organización de fidelización no coincide con la sesión.")
        self.organization_id = organization_id or current_scope
        if not isinstance(self.organization_id, int):
            raise HTTPException(403, "Se requiere una organización autenticada.")
        if current_scope is None:
            db.info["organization_id"] = self.organization_id
        self._expiration_changed = False

    def require_feature(self):
        # Loyalty checks often run inside the sale/payment transaction. Do not
        # let plan-expiration housekeeping commit that transaction early.
        access = PlanAccessService(self.db).require_feature("fidelizacion_clientes", commit_expiration=False)
        if access.organization_id != self.organization_id:
            raise HTTPException(403, "La fidelización no pertenece a la organización autenticada.")

    def program(self, *, lock: bool = False) -> LoyaltyProgram | None:
        query = select(LoyaltyProgram).where(LoyaltyProgram.organization_id == self.organization_id)
        if lock:
            query = query.with_for_update()
        return self.db.scalar(query)

    def configure(self, payload: dict, actor: Usuario) -> LoyaltyProgram:
        self.require_feature()
        row = self.program(lock=True)
        if row is None:
            row = LoyaltyProgram(organization_id=self.organization_id)
            self.db.add(row)
        for key in ("active", "name", "points_per_currency", "currency_per_point", "minimum_redeem_points", "max_discount_percent", "expiration_days"):
            if key in payload:
                setattr(row, key, payload[key])
        row.updated_at = datetime.now(timezone.utc)
        self.db.flush()
        AuditService.record(self.db, organization_id=self.organization_id, actor_id=actor.id_usuario,
            actor_role=actor.rol.nombre, action="PROGRAMA_FIDELIZACION_ACTUALIZADO", entity="LoyaltyProgram",
            entity_id=row.id, details={"active": row.active})
        return row

    def save_tiers(self, tiers: list[dict], actor: Usuario) -> list[LoyaltyTier]:
        self.require_feature()
        if len(tiers) > 10 or len({item["code"] for item in tiers}) != len(tiers):
            raise HTTPException(422, "La configuración de niveles no es válida.")
        existing = {row.code: row for row in self.db.scalars(select(LoyaltyTier).where(
            LoyaltyTier.organization_id == self.organization_id).with_for_update()).all()}
        requested_codes = {item["code"] for item in tiers}
        for code, row in existing.items():
            if code not in requested_codes:
                self.db.delete(row)
        result = []
        for item in tiers:
            row = existing.get(item["code"])
            if row is None:
                row = LoyaltyTier(organization_id=self.organization_id, **item)
                self.db.add(row)
            else:
                row.name, row.minimum_points = item["name"], item["minimum_points"]
            result.append(row)
        AuditService.record(self.db, organization_id=self.organization_id, actor_id=actor.id_usuario,
            actor_role=actor.rol.nombre, action="NIVELES_FIDELIZACION_ACTUALIZADOS", entity="LoyaltyTier",
            entity_id=None, details={"count": len(result)})
        self.db.flush()
        return result

    def _account(self, customer_id: int, *, create: bool = False, lock: bool = False) -> LoyaltyAccount | None:
        customer = self.db.scalar(select(Cliente).join(Usuario).where(
            Cliente.id_cliente == customer_id, Usuario.id_organizacion == self.organization_id))
        if customer is None:
            raise HTTPException(404, "Cliente no encontrado en esta organización.")
        query = select(LoyaltyAccount).where(LoyaltyAccount.organization_id == self.organization_id,
                                               LoyaltyAccount.customer_id == customer_id)
        if lock:
            query = query.with_for_update()
        account = self.db.scalar(query)
        if account is None and create:
            account = LoyaltyAccount(organization_id=self.organization_id, customer_id=customer_id)
            self.db.add(account)
            self.db.flush()
        return account

    def snapshot(self, customer_id: int) -> dict:
        self.require_feature()
        program = self.program()
        account = self._account(customer_id, create=False)
        if account is not None:
            account = self._expire_points(account)
        balance = account.balance if account else 0
        tiers = self.db.scalars(select(LoyaltyTier).where(
            LoyaltyTier.organization_id == self.organization_id).order_by(LoyaltyTier.minimum_points)).all()
        tier = next((item for item in reversed(tiers) if item.minimum_points <= balance), None)
        next_tier = next((item for item in tiers if item.minimum_points > balance), None)
        movements = []
        if account:
            movements = [{"id": row.id, "kind": row.kind, "points": row.points,
                          "amount": str(row.amount), "created_at": row.created_at.isoformat(),
                          "expires_at": row.expires_at.isoformat() if row.expires_at else None}
                         for row in self.db.scalars(select(LoyaltyLedger).where(
                             LoyaltyLedger.organization_id == self.organization_id,
                             LoyaltyLedger.account_id == account.id).order_by(LoyaltyLedger.created_at.desc()).limit(100)).all()]
        if self._expiration_changed:
            self.db.commit()
        return {"program": self.program_dict(program) if program else None, "balance": balance,
                "earned_total": account.earned_total if account else 0,
                "redeemed_total": account.redeemed_total if account else 0,
                "expired_total": account.expired_total if account else 0,
                "tier": {"code": tier.code, "name": tier.name, "minimum_points": tier.minimum_points} if tier else None,
                "next_tier": {"code": next_tier.code, "name": next_tier.name, "minimum_points": next_tier.minimum_points} if next_tier else None,
                "movements": movements}

    def _expire_points(self, account: LoyaltyAccount) -> LoyaltyAccount:
        now = datetime.now(timezone.utc)
        account = self.db.scalar(select(LoyaltyAccount).where(
            LoyaltyAccount.id == account.id, LoyaltyAccount.organization_id == self.organization_id
        ).with_for_update()) or account
        earned = self.db.scalars(select(LoyaltyLedger).where(
            LoyaltyLedger.organization_id == self.organization_id,
            LoyaltyLedger.account_id == account.id,
            LoyaltyLedger.kind == "ACUMULACION",
            LoyaltyLedger.points > 0,
            LoyaltyLedger.expires_at.is_not(None),
            LoyaltyLedger.expires_at <= now,
        ).with_for_update()).all()
        for row in earned:
            event = f"expire:earning:{row.id}"
            if self.db.scalar(select(LoyaltyLedger.id).where(
                LoyaltyLedger.organization_id == self.organization_id, LoyaltyLedger.event_key == event)):
                continue
            prior_adjustments = self.db.scalars(select(LoyaltyLedger).where(
                LoyaltyLedger.organization_id == self.organization_id,
                LoyaltyLedger.account_id == account.id,
                LoyaltyLedger.order_id == row.order_id,
                LoyaltyLedger.kind.in_(("REVERSO", "EXPIRACION")),
            )).all()
            already_adjusted = sum(-entry.points for entry in prior_adjustments if entry.points < 0)
            amount = min(account.balance, max(0, row.points - already_adjusted))
            account.balance -= amount
            account.expired_total += amount
            self._expiration_changed = True
            self.db.add(LoyaltyLedger(organization_id=self.organization_id, account_id=account.id,
                order_id=row.order_id, event_key=event, kind="EXPIRACION", points=-amount,
                amount=Decimal("0.00"), expires_at=row.expires_at))
            AuditService.record(self.db, organization_id=self.organization_id, actor_id=None,
                actor_role="SISTEMA", action="PUNTOS_VENCIDOS", entity="LoyaltyLedger",
                entity_id=row.id, details={"points": amount}, dedupe_key=f"loyalty-expire:{self.organization_id}:{row.id}")
        if earned:
            self.db.flush()
        return account

    @staticmethod
    def program_dict(row: LoyaltyProgram) -> dict:
        return {"active": row.active, "name": row.name, "points_per_currency": str(row.points_per_currency),
                "currency_per_point": str(row.currency_per_point), "minimum_redeem_points": row.minimum_redeem_points,
                "max_discount_percent": str(row.max_discount_percent), "expiration_days": row.expiration_days,
                "updated_at": row.updated_at.isoformat()}

    def accrue_for_order(self, order_id: int, actor_id: int | None = None) -> int:
        order = self.db.scalar(select(Pedido).where(Pedido.id_pedido == order_id).with_for_update())
        if order is None or order.id_cliente is None:
            return 0
        if self.db.scalar(select(Pago.id_pago).where(Pago.id_pedido == order_id, Pago.estado == "PAGADO")) is None:
            return 0
        customer = self._account(order.id_cliente, create=False)
        # Verify actual client belongs to same tenant even when no account exists.
        client = self.db.scalar(select(Cliente).join(Usuario).where(
            Cliente.id_cliente == order.id_cliente, Usuario.id_organizacion == self.organization_id))
        if client is None:
            return 0
        program = self.program(lock=True)
        if program is None or not program.active:
            return 0
        try:
            self.require_feature()
        except HTTPException:
            return 0
        event_key = f"earn:order:{order_id}"
        if self.db.scalar(select(LoyaltyLedger.id).where(
            LoyaltyLedger.organization_id == self.organization_id, LoyaltyLedger.event_key == event_key)):
            return 0
        account = customer or self._account(order.id_cliente, create=True, lock=True)
        points = int((Decimal(order.total) * Decimal(program.points_per_currency)).to_integral_value(rounding=ROUND_DOWN))
        if points <= 0:
            return 0
        expires = datetime.now(timezone.utc) + timedelta(days=program.expiration_days) if program.expiration_days else None
        account.balance += points
        account.earned_total += points
        self.db.add(LoyaltyLedger(organization_id=self.organization_id, account_id=account.id, order_id=order_id,
            event_key=event_key, kind="ACUMULACION", points=points, amount=order.total, expires_at=expires))
        AuditService.record(self.db, organization_id=self.organization_id, actor_id=actor_id,
            actor_role="SISTEMA" if actor_id is None else "USUARIO", action="PUNTOS_ACUMULADOS",
            entity="Pedido", entity_id=order_id, details={"points": points}, dedupe_key=f"loyalty-earn:{self.organization_id}:{order_id}")
        return points

    def estimate_redemption(self, customer_id: int, amount: Decimal, requested_points: int,
                            *, persist_expiration: bool = True) -> dict:
        self.require_feature()
        program = self.program()
        account = self._account(customer_id, create=False)
        if account is not None:
            account = self._expire_points(account)
        if persist_expiration and self._expiration_changed:
            self.db.commit()
        if not program or not program.active or not account or requested_points <= 0:
            return {"points": 0, "discount": "0.00", "balance": account.balance if account else 0}
        if requested_points < program.minimum_redeem_points or requested_points > account.balance:
            raise HTTPException(409, "Los puntos solicitados no alcanzan el mínimo o superan el saldo.")
        max_discount = (amount * Decimal(program.max_discount_percent) / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        discount = min((Decimal(requested_points) * Decimal(program.currency_per_point)).quantize(Decimal("0.01"), rounding=ROUND_DOWN), max_discount)
        points_used = min(requested_points, int((discount / Decimal(program.currency_per_point)).to_integral_value(rounding=ROUND_DOWN)))
        return {"points": points_used, "discount": str(discount), "balance": account.balance}

    def redeem_for_order(self, customer_id: int, order: Pedido, requested_points: int, actor_id: int | None = None) -> dict:
        if requested_points <= 0:
            return {"points": 0, "discount": Decimal("0.00")}
        program = self.program(lock=True)
        account = self._account(customer_id, create=False, lock=True)
        if account is not None:
            account = self._expire_points(account)
        if not program or not program.active or account is None:
            raise HTTPException(409, "La fidelización no está activa para este cliente.")
        result = self.estimate_redemption(customer_id, Decimal(order.total), requested_points,
                                          persist_expiration=False)
        points, discount = result["points"], Decimal(result["discount"])
        if points <= 0 or discount <= 0:
            raise HTTPException(409, "No es posible aplicar ese canje a esta compra.")
        account.balance -= points
        account.redeemed_total += points
        order.total = max(Decimal("0.00"), Decimal(order.total) - discount)
        self.db.add(LoyaltyLedger(organization_id=self.organization_id, account_id=account.id, order_id=order.id_pedido,
            event_key=f"redeem:order:{order.id_pedido}", kind="CANJE", points=-points, amount=discount))
        AuditService.record(self.db, organization_id=self.organization_id, actor_id=actor_id,
            actor_role="USUARIO", action="PUNTOS_CANJEADOS", entity="Pedido", entity_id=order.id_pedido,
            details={"points": points, "discount": str(discount)}, dedupe_key=f"loyalty-redeem:{self.organization_id}:{order.id_pedido}")
        return {"points": points, "discount": discount}

    def reverse_for_return(self, return_id: int, actor_id: int | None = None) -> int:
        from app.models.comercio import Devolucion
        returned = self.db.get(Devolucion, return_id)
        if returned is None or returned.estado != "COMPLETADA":
            return 0
        detail = self.db.get(PedidoDetalle, returned.id_detalle)
        order = self.db.get(Pedido, detail.id_pedido) if detail else None
        if order is None or order.id_cliente is None:
            return 0
        earn = self.db.scalar(select(LoyaltyLedger).where(
            LoyaltyLedger.organization_id == self.organization_id,
            LoyaltyLedger.order_id == order.id_pedido, LoyaltyLedger.kind == "ACUMULACION").with_for_update())
        if earn is None:
            return 0
        key = f"reversal:return:{return_id}"
        if self.db.scalar(select(LoyaltyLedger.id).where(LoyaltyLedger.organization_id == self.organization_id,
                                                         LoyaltyLedger.event_key == key)):
            return 0
        account = self._account(order.id_cliente, lock=True)
        if account is None:
            return 0
        return_amount = Decimal(detail.precio_unitario) * returned.cantidad
        completed_returns = self.db.execute(select(
            Devolucion.__table__.c.cantidad, PedidoDetalle.__table__.c.precio_unitario
        ).select_from(PedidoDetalle.__table__.join(
            Devolucion.__table__, Devolucion.__table__.c.id_detalle == PedidoDetalle.__table__.c.id_detalle
        )).where(PedidoDetalle.__table__.c.id_pedido == order.id_pedido,
                 Devolucion.__table__.c.estado == "COMPLETADA").correlate(None)).all()
        cumulative_amount = sum((Decimal(price) * quantity for quantity, price in completed_returns), Decimal("0.00"))
        details = self.db.scalars(select(PedidoDetalle).where(PedidoDetalle.id_pedido == order.id_pedido)).all()
        original_value = sum((Decimal(item.precio_unitario) * item.cantidad for item in details), Decimal("0.00"))
        ratio_points = int((Decimal(earn.points) * min(cumulative_amount, original_value) / original_value).to_integral_value(rounding=ROUND_DOWN)) if original_value else 0
        already_reversed = -(self.db.scalar(select(func.coalesce(func.sum(LoyaltyLedger.points), 0)).where(
            LoyaltyLedger.organization_id == self.organization_id, LoyaltyLedger.order_id == order.id_pedido,
            LoyaltyLedger.kind == "REVERSO")) or 0)
        points = max(0, ratio_points - already_reversed)
        points = min(points, account.balance)
        account.balance -= points
        self.db.add(LoyaltyLedger(organization_id=self.organization_id, account_id=account.id, order_id=order.id_pedido,
            event_key=key, kind="REVERSO", points=-points, amount=return_amount))
        AuditService.record(self.db, organization_id=self.organization_id, actor_id=actor_id,
            actor_role="USUARIO" if actor_id else "SISTEMA", action="PUNTOS_REVERTIDOS", entity="Devolucion",
            entity_id=return_id, details={"points": points}, dedupe_key=f"loyalty-reversal:{self.organization_id}:{return_id}")
        return points

    def admin_summary(self) -> dict:
        self.require_feature()
        accounts = self.db.scalars(select(LoyaltyAccount).where(LoyaltyAccount.organization_id == self.organization_id)).all()
        for account in accounts:
            self._expire_points(account)
        if self._expiration_changed:
            self.db.commit()
        customer_by_account = {account.id: account.customer_id for account in accounts}
        recent = self.db.scalars(select(LoyaltyLedger).where(LoyaltyLedger.organization_id == self.organization_id)
                                 .order_by(LoyaltyLedger.created_at.desc()).limit(500)).all()
        return {"program": self.program_dict(self.program()) if self.program() else None,
                "customers": [{"customer_id": a.customer_id, "name": f"{a.customer.usuario.nombres} {a.customer.usuario.apellidos}",
                               "email": a.customer.usuario.correo, "balance": a.balance, "earned_total": a.earned_total,
                               "redeemed_total": a.redeemed_total, "expired_total": a.expired_total} for a in accounts],
                "metrics": {"customers": len(accounts), "earned": sum(max(x.points, 0) for x in recent),
                            "redeemed": sum(-x.points for x in recent if x.points < 0 and x.kind == "CANJE"),
                            "expired": sum(-x.points for x in recent if x.kind == "EXPIRACION")},
                "ledger": [{"id": x.id, "customer_id": customer_by_account.get(x.account_id), "order_id": x.order_id, "kind": x.kind,
                            "points": x.points, "amount": str(x.amount), "created_at": x.created_at.isoformat()}
                           for x in recent]}

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.database.plan_seed import seed_commercial_plans
from app.models.plan import Plan, PlanCaracteristica


def test_seed_creates_three_plans_and_feature_matrix_idempotently(db):
    assert seed_commercial_plans(db) == 43
    db.commit()

    plans = {plan.codigo: plan for plan in db.scalars(select(Plan)).all()}
    assert set(plans) == {"ESTILO", "MODA", "GLAMOUR"}
    assert plans["ESTILO"].max_sucursales == 2
    assert plans["MODA"].max_sucursales == 10
    assert plans["GLAMOUR"].max_sucursales is None
    assert [len(plans[code].caracteristicas) for code in ("ESTILO", "MODA", "GLAMOUR")] == [8, 13, 19]
    assert "reportes_ia" not in {feature.codigo for feature in plans["ESTILO"].caracteristicas}
    assert "reportes_ia" in {feature.codigo for feature in plans["MODA"].caracteristicas}
    assert "reportes_ia" in {feature.codigo for feature in plans["GLAMOUR"].caracteristicas}

    plans["MODA"].max_sucursales = 12
    moda_catalog = next(feature for feature in plans["MODA"].caracteristicas if feature.codigo == "catalogo")
    moda_catalog.habilitada = False
    moda_catalog.limite = 100
    moda_catalog.configuracion = {"modo": "compacto"}
    db.commit()

    assert seed_commercial_plans(db) == 0
    db.commit()
    assert db.scalar(select(func.count()).select_from(Plan)) == 3
    assert db.scalar(select(func.count()).select_from(PlanCaracteristica)) == 40
    db.refresh(plans["MODA"])
    db.refresh(moda_catalog)
    assert plans["MODA"].max_sucursales == 12
    assert moda_catalog.habilitada is False
    assert moda_catalog.limite == 100
    assert moda_catalog.configuracion == {"modo": "compacto"}


def test_seed_migrates_legacy_ai_entitlement_without_changing_its_setting(db):
    plan = Plan(codigo="MODA", nombre="Plan Moda", max_sucursales=10)
    db.add(plan)
    db.flush()
    db.add(PlanCaracteristica(
        plan_id=plan.id_plan, codigo="reportes_gemini", nombre="Legacy",
        habilitada=False, limite=3, configuracion={"scope": "tenant"},
    ))
    db.commit()

    seed_commercial_plans(db)
    db.flush()
    feature = db.scalar(select(PlanCaracteristica).where(
        PlanCaracteristica.plan_id == plan.id_plan, PlanCaracteristica.codigo == "reportes_ia"
    ))
    assert feature is not None
    assert feature.habilitada is False
    assert feature.limite == 3
    assert feature.configuracion == {"scope": "tenant"}


def test_plan_codes_are_unique(db):
    db.add_all([
        Plan(codigo="ESTILO", nombre="Plan Estilo", max_sucursales=2),
        Plan(codigo="ESTILO", nombre="Duplicado", max_sucursales=2),
    ])
    try:
        db.commit()
        assert False, "La base debe rechazar códigos de plan duplicados"
    except IntegrityError:
        db.rollback()


def test_plan_characteristic_code_is_unique_per_plan(db):
    plan = Plan(codigo="PRUEBA", nombre="Plan de prueba", max_sucursales=1)
    db.add(plan)
    db.flush()
    db.add_all([
        PlanCaracteristica(plan_id=plan.id_plan, codigo="catalogo", nombre="Catálogo"),
        PlanCaracteristica(plan_id=plan.id_plan, codigo="catalogo", nombre="Duplicada"),
    ])
    try:
        db.commit()
        assert False, "La base debe rechazar características repetidas en el mismo plan"
    except IntegrityError:
        db.rollback()


def test_branch_limits_allow_fixed_and_unlimited_plans_but_reject_nonpositive(db):
    db.add_all([
        Plan(codigo="DOS", nombre="Dos", max_sucursales=2),
        Plan(codigo="DIEZ", nombre="Diez", max_sucursales=10),
        Plan(codigo="ILIMITADO", nombre="Ilimitado", max_sucursales=None),
    ])
    db.commit()
    limits = {row.codigo: row.max_sucursales for row in db.scalars(select(Plan)).all()}
    assert limits == {"DOS": 2, "DIEZ": 10, "ILIMITADO": None}

    db.add(Plan(codigo="INVALIDO", nombre="Inválido", max_sucursales=0))
    try:
        db.commit()
        assert False, "La base debe rechazar un límite fijo no positivo"
    except IntegrityError:
        db.rollback()

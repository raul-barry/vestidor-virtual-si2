from sqlalchemy import select

from app.database.seed import INITIAL_ROLES, seed_roles
from app.models.rol import Rol


def test_seed_roles_creates_missing_roles_once(db) -> None:
    assert seed_roles(db) == len(INITIAL_ROLES)
    db.commit()

    assert set(db.scalars(select(Rol.nombre)).all()) == set(INITIAL_ROLES)
    assert seed_roles(db) == 0


def test_seed_initial_data_creates_all_users_and_is_idempotent(db) -> None:
    from app.database.seed import seed_initial_data
    created = seed_initial_data(db)
    assert created["usuarios"] == 4

    created_second = seed_initial_data(db)
    assert created_second["usuarios"] == 0


from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database.seed import seed_initial_data
from app.main import app
from app.models.rol import Rol
from app.models.usuario import Usuario


def test_role_change_blocks_customer_endpoints_even_with_existing_customer_record(db):
    seed_initial_data(db)
    db.commit()
    client = TestClient(app)
    login = client.post('/api/auth/login', json={
        'correo': 'cliente@vestidor.local', 'password': 'Cliente123!'})
    headers = {'Authorization': 'Bearer ' + login.json()['access_token']}
    user = db.scalar(select(Usuario).where(Usuario.correo == 'cliente@vestidor.local'))
    user.id_rol = db.scalar(select(Rol.id_rol).where(Rol.nombre == 'CAJERO'))
    db.commit()
    for path in ['/api/cart', '/api/orders', '/api/payments/order/1']:
        assert client.get(path, headers=headers).status_code == 403

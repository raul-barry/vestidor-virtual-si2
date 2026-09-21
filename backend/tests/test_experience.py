from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database.seed import seed_initial_data
from app.main import app
from app.models.inventario import Inventario
from app.models.recurso_virtual import RecursoVirtual
from app.models.bitacora import Bitacora
from test_commerce import headers


def setup_client(db):
    seed_initial_data(db)
    db.commit()
    client = TestClient(app)
    return client, headers(client, "cliente")


def test_customer_catalog_fitting_and_recommendations(db):
    client, auth = setup_client(db)
    products = client.get('/api/catalog/products').json()
    product = next(p for p in products if p['nombre'] == 'Camisa Oxford Azul')
    product_id = product['id_producto']
    variants = client.get(f'/api/catalog/products/{product_id}/variants').json()['variantes']
    variant = next(v for v in variants if v['talla'] == 'L')
    for kind in ('vista', 'favorita', 'seleccion'):
        signal = {'tipo': kind, 'id_producto': product_id, 'id_variante': variant['id_variante'] if kind == 'seleccion' else None}
        for _ in range(2):
            assert client.post('/api/experience/preferences', headers=auth, json=signal).status_code == 201
    assert len(db.scalars(select(Bitacora).where(Bitacora.accion.like('preferencia:%'))).all()) == 3
    fitting = client.get(f'/api/experience/virtual-fitting/{product_id}', headers=auth)
    assert fitting.status_code == 200
    resource = fitting.json()['recursos'][0]
    assert resource['tipo_recurso'] == 'imagen'
    asset = client.get(resource['url_archivo'])
    assert asset.status_code == 200 and '<svg' in asset.text
    recommendations = client.get('/api/experience/recommendations', headers=auth).json()
    assert recommendations[0]['id_producto'] == product_id
    assert recommendations[0]['talla'] == 'L'
    assert 'categorías favoritas' in recommendations[0]['motivo']
    assert any('Complementa' in r['motivo'] and r['garment'] == 'pants' for r in recommendations)
    assert len({r['id_producto'] for r in recommendations}) == len(recommendations)
    assert client.get('/api/recommendations', headers=auth).json() == recommendations
    assert seed_initial_data(db)['recursos_virtuales'] == 0


def test_unavailable_resources_stock_and_authentication(db):
    client, auth = setup_client(db)
    rows = client.get('/api/experience/fitting', headers=auth).json()
    product_id = rows[0]['id_producto']
    path = f'/api/experience/virtual-fitting/{product_id}'
    assert client.get(path).status_code == 401
    assert client.get('/api/experience/recommendations').status_code == 401
    assert client.get('/api/experience/virtual-fitting/99999', headers=auth).status_code == 404
    other = next(r for r in rows if r['id_producto'] != product_id)
    assert client.post('/api/experience/preferences', headers=auth, json={
        'tipo': 'seleccion', 'id_producto': product_id, 'id_variante': other['id_variante']}).status_code == 422
    resource = db.scalar(select(RecursoVirtual).where(RecursoVirtual.id_producto == product_id))
    resource.estado = 'INACTIVO'
    db.commit()
    assert client.get(path, headers=auth).status_code == 404
    resource.estado = 'ACTIVO'
    resource.tipo_recurso = 'modelo_3d'
    db.commit()
    assert client.get(path, headers=auth).status_code == 404
    resource.tipo_recurso = 'imagen'
    for inventory in db.scalars(select(Inventario)).all():
        inventory.stock_disponible = 0
    db.commit()
    assert client.get(path, headers=auth).status_code == 404
    assert client.get('/api/experience/recommendations', headers=auth).json() == []
    assert client.get('/api/experience/fitting', headers=auth).json() == []


def test_purchase_history_and_user_isolation(db):
    client, auth = setup_client(db)
    rows = client.get('/api/experience/recommendations', headers=auth).json()
    assert all(r['puntuacion'] == 0 for r in rows)
    product = rows[-1]
    client.post('/api/cart/items', headers=auth, json={'id_variante': product['id_variante'], 'cantidad': 1})
    order = client.post('/api/orders', headers=auth).json()
    # Unpaid orders do not count as purchases.
    assert all(r['puntuacion'] == 0 for r in client.get('/api/recommendations', headers=auth).json())
    payment = client.post('/api/payments', headers=auth, json={'id_pedido': order['id_pedido'], 'metodo_pago': 'QR'}).json()
    assert client.put(f"/api/payments/{payment['id_pago']}/approve", headers=auth).status_code == 200
    recommended = client.get('/api/recommendations', headers=auth).json()[0]
    assert recommended['id_producto'] == product['id_producto']
    assert 'compras' in recommended['motivo']
    admin = headers(client, 'admin')
    assert all(r['puntuacion'] == 0 for r in client.get('/api/recommendations', headers=admin).json())

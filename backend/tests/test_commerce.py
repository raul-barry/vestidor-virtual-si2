from datetime import date, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.database.seed import seed_initial_data
from app.main import app
from app.models.inventario import Inventario
from app.models.cliente import Cliente
from app.models.pedido_detalle import PedidoDetalle
from app.models.usuario import Usuario


def headers(client, name):
    password = {'admin':'Admin123!', 'cajero':'Cajero123!', 'cliente':'Cliente123!', 'encargado':'Encargado123!'}[name]
    login = client.post('/api/auth/login', json={'correo':f'{name}@vestidor.local','password':password})
    assert login.status_code == 200
    return {'Authorization':'Bearer '+login.json()['access_token']}


def test_commercial_flow(db):
    seed_initial_data(db)
    db.commit()
    client = TestClient(app)
    admin, cashier, customer = [headers(client, n) for n in ('admin', 'cajero', 'cliente')]
    supplier = client.post('/api/commerce/masters/suppliers', headers=admin, json={'nombre':'Proveedor nuevo','detalle':'Contacto'})
    assert supplier.status_code == 201
    collection = client.post('/api/commerce/masters/collections', headers=admin, json={'nombre':'Colección nueva'})
    assert collection.status_code == 201
    product = client.get('/api/commerce/products', headers=admin).json()[0]
    assert client.put(f"/api/commerce/products/{product['id_producto']}/links", headers=admin, json={
        'id_proveedor':supplier.json()['id_proveedor'], 'id_coleccion':collection.json()['id_coleccion']}).status_code == 200
    options = client.get('/api/commerce/pos/options', headers=cashier).json()
    item = options['inventario'][0]
    inv = db.get(Inventario, item['id_inventario'])
    promotion = {'id_producto':inv.variante.id_producto, 'nombre':'Mitad', 'descuento':50,
                 'inicio':str(date.today()), 'fin':str(date.today()+timedelta(days=1))}
    assert client.post('/api/commerce/promotions', headers=customer, json=promotion).status_code == 403
    result = client.post('/api/commerce/promotions', headers=admin, json=promotion)
    assert result.status_code == 201
    assert client.post('/api/commerce/promotions', headers=admin, json={**promotion,'fin':'2000-01-01'}).status_code == 422
    sale = {'id_cliente':options['clientes'][0]['id_cliente'],'metodo_pago':'EFECTIVO','items':[{'id_inventario':inv.id_inventario,'cantidad':2}]}
    original = inv.stock_disponible
    assert client.post('/api/commerce/pos', headers=customer, json=sale).status_code == 403
    result = client.post('/api/commerce/pos', headers=cashier, json=sale)
    assert result.status_code == 201, result.text
    assert Decimal(str(result.json()['total'])) == inv.variante.producto.precio_base
    db.refresh(inv)
    assert inv.stock_disponible == original - 2
    order_id = result.json()['id_pedido']
    options = client.get('/api/commerce/returns/options', headers=admin)
    assert options.status_code == 200, options.text
    detail = next(d for d in options.json()['detalles'] if d['id_pedido']==order_id)
    request = {'id_detalle':detail['id_detalle'],'id_inventario':inv.id_inventario,'cantidad':2,'motivo':'Talla incorrecta'}
    assert client.post('/api/commerce/returns', headers=cashier, json=request).status_code == 403
    assert client.post('/api/commerce/returns', headers=admin, json=request).status_code == 201
    assert client.post('/api/commerce/returns', headers=admin, json=request).status_code == 409
    db.refresh(inv)
    assert inv.stock_disponible == original
    actions = client.get('/api/commerce/audit', headers=admin).json()
    assert any('Venta presencial' in a['accion'] for a in actions)
    assert any('Devolución' in a['accion'] for a in actions)
    assert client.get('/api/admin/reports/sales',headers=admin).status_code == 200


def test_experience_and_session_revocation(db):
    seed_initial_data(db)
    db.commit()
    client = TestClient(app)
    admin, customer = headers(client,'admin'), headers(client,'cliente')
    rows = client.get('/api/experience/recommendations?talla=M&color=Azul',headers=customer).json()
    assert rows and rows[0]['talla']=='M' and rows[0]['color']=='Azul'
    fitting = client.get('/api/experience/fitting',headers=customer).json()
    assert fitting
    assert client.post('/api/experience/fitting',headers=customer,json={'id_variante':fitting[0]['id_variante']}).status_code == 200
    assert client.get('/api/experience/sessions',headers=customer).status_code == 403
    sessions = client.get('/api/experience/sessions',headers=admin).json()
    customer_id = db.scalar(select(Usuario.id_usuario).where(Usuario.correo=='cliente@vestidor.local'))
    session = next(s for s in sessions if s['id_usuario']==customer_id)
    assert client.delete(f"/api/experience/sessions/{session['id_sesion']}",headers=admin).status_code == 200
    assert client.get('/api/experience/recommendations',headers=customer).status_code == 401
    customer = headers(client,'cliente')
    assert client.post('/api/auth/logout',headers=customer).status_code == 200
    assert client.get('/api/experience/recommendations',headers=customer).status_code == 401


def test_master_changes_persist_and_are_protected(db):
    seed_initial_data(db)
    db.commit()
    client = TestClient(app)
    admin, customer = headers(client,'admin'), headers(client,'cliente')
    for path, payload, key in [('categories',{'nombre':'Nueva categoría','descripcion':'Descripción'},'id_categoria'),
                               ('sizes',{'nombre':'XXL'},'id_talla'), ('colors',{'nombre':'Naranja'},'id_color'),
                               ('branches',{'nombre':'Norte','direccion':'Av Norte','ciudad':'La Paz'},'id_sucursal')]:
        endpoint='/api/admin/'+path
        assert client.post(endpoint,headers=customer,json=payload).status_code==403
        created=client.post(endpoint,headers=admin,json=payload)
        assert created.status_code==201, created.text
        item_id=created.json()[key]
        assert client.put(f'{endpoint}/{item_id}',headers=admin,json={'nombre':payload['nombre']+' editado'}).status_code==200
        rows=client.get(endpoint,headers=admin).json()
        assert next(r for r in rows if r[key]==item_id)['nombre'].endswith('editado')


def test_branch_scope_and_city_rename(db):
    from app.models.sucursal import Sucursal
    seed_initial_data(db)
    db.commit()
    client = TestClient(app)
    admin, staff, cashier = [headers(client, n) for n in ('admin', 'encargado', 'cajero')]
    branch = client.post('/api/admin/branches', headers=admin, json={'nombre':'Otra sucursal','direccion':'Norte','ciudad':'Otra ciudad'}).json()
    cities = client.get('/api/commerce/masters/cities', headers=admin).json()
    city = next(c for c in cities if c['nombre']=='Otra ciudad')
    assert client.put(f"/api/commerce/masters/cities/{city['id_ciudad']}",headers=admin,json={'nombre':'Ciudad renombrada'}).status_code == 200
    assert db.get(Sucursal, branch['id_sucursal']).ciudad == 'Ciudad renombrada'
    assert client.delete(f"/api/commerce/masters/cities/{city['id_ciudad']}",headers=admin).status_code == 409
    original = db.scalar(select(Inventario))
    created = client.post('/api/admin/inventory', headers=admin, json={'id_sucursal':branch['id_sucursal'],'id_variante':original.id_variante,'stock':5}).json()
    path = f"/api/admin/inventory/{created['id_inventario']}/increase"
    assert client.post(path, headers=staff, json={'cantidad':1,'motivo':'Entrada'}).status_code == 403
    inventory = client.get('/api/admin/inventory',headers=staff).json()
    assert created['id_inventario'] not in [i['id_inventario'] for i in inventory]
    customer_id = db.scalar(select(Cliente.id_cliente))
    sale = {'id_cliente':customer_id, 'metodo_pago':'EFECTIVO','items':[{'id_inventario':created['id_inventario'],'cantidad':1}]}
    assert client.post('/api/commerce/pos', headers=cashier, json=sale).status_code == 403


def test_failed_payment_can_be_retried_without_duplicating_charge(db):
    seed_initial_data(db)
    db.commit()
    client = TestClient(app)
    customer = headers(client,'cliente')
    inv = db.scalar(select(Inventario))
    client.post('/api/cart/items',headers=customer,json={'id_variante':inv.id_variante,'cantidad':1})
    order = client.post('/api/orders',headers=customer).json()
    request = {'id_pedido':order['id_pedido'],'metodo_pago':'QR'}
    payment = client.post('/api/payments',headers=customer,json=request).json()
    assert client.put(f"/api/payments/{payment['id_pago']}/reject",headers=customer).status_code == 200
    retry = client.post('/api/payments',headers=customer,json=request)
    assert retry.status_code == 200 and retry.json()['id_pago'] == payment['id_pago']
    assert client.put(f"/api/payments/{payment['id_pago']}/approve",headers=customer).status_code == 200

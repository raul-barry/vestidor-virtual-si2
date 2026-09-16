"""Opt-in journey against the running development API and PostgreSQL."""
import os
from datetime import date, timedelta
from uuid import uuid4
import httpx
import pytest


@pytest.mark.skipif(not os.getenv("VV_E2E_BASE_URL"), reason="Requires running development services")
def test_four_role_journey_on_live_database():
    suffix = uuid4().hex[:10]
    with httpx.Client(base_url=os.environ["VV_E2E_BASE_URL"], timeout=30) as client:
        def call(method, path, token=None, body=None, expected=200):
            response = client.request(method, '/api'+path, headers={'Authorization':f'Bearer {token}'} if token else {}, json=body)
            assert response.status_code == expected, f'{method} {path}: {response.status_code} {response.text[:300]}'
            return response.json() if response.content else None

        def login(name, password):
            return call('POST','/auth/login',body={'correo':name,'password':password})['access_token']

        admin = login('admin@vestidor.local','Admin123!')
        category = call('POST','/admin/categories',admin,{'nombre':f'Camisas {suffix}','descripcion':'Prueba integral'},201)
        size = call('POST','/admin/sizes',admin,{'nombre':f'M-{suffix}'},201)
        color = call('POST','/admin/colors',admin,{'nombre':f'Azul-{suffix}'},201)
        branch = call('POST','/admin/branches',admin,{'nombre':f'Sucursal {suffix}','direccion':'Centro','ciudad':f'Ciudad {suffix}'},201)
        product = call('POST','/admin/products',admin,{'nombre':f'Camisa {suffix}','descripcion':'Prueba','precio_base':'100','id_categoria':category['id_categoria']},201)
        call('PUT',f"/admin/products/{product['id_producto']}",admin,{'descripcion':'Prenda de prueba integral'})
        variant = call('POST','/admin/variants',admin,{'id_producto':product['id_producto'],'id_talla':size['id_talla'],'id_color':color['id_color'],'sku':f'E2E-{suffix}'},201)
        inventory = call('POST','/admin/inventory',admin,{'id_variante':variant['id_variante'],'id_sucursal':branch['id_sucursal'],'stock':10},201)
        for kind in ('suppliers','collections'):
            row = call('POST',f'/commerce/masters/{kind}',admin,{'nombre':f'Prueba {suffix}'},201)
            if kind == 'suppliers': supplier = row['id_proveedor']
            else: collection = row['id_coleccion']
        call('PUT',f"/commerce/products/{product['id_producto']}/links",admin,{'id_proveedor':supplier,'id_coleccion':collection})
        call('POST','/commerce/promotions',admin,{'id_producto':product['id_producto'],'nombre':f'Promo {suffix}','descuento':20,'inicio':str(date.today()),'fin':str(date.today()+timedelta(days=1))},201)
        call('GET','/admin/users',admin)
        call('GET','/admin/reports/dashboard',admin)

        email = f'journey-{suffix}@example.com'
        call('POST','/auth/register',body={'nombres':'Prueba','apellidos':suffix,'correo':email,'password':'Cliente123!'},expected=201)
        customer = login(email,'Cliente123!')
        call('PUT','/users/profile',customer,{'telefono':'70000000'})
        catalog = call('GET',f'/catalog/products/search?nombre={suffix}&talla=M-{suffix}',customer)
        assert len(catalog) == 1 and str(catalog[0]['precio_base']) == '80.00'
        call('GET',f"/catalog/products/{product['id_producto']}/variants",customer)
        call('GET',f"/catalog/products/{product['id_producto']}/availability",customer)
        call('POST','/cart/items',customer,{'id_variante':variant['id_variante'],'cantidad':2})
        order = call('POST','/orders',customer,expected=201)
        payment = call('POST','/payments',customer,{'id_pedido':order['id_pedido'],'metodo_pago':'QR'})
        call('PUT',f"/payments/{payment['id_pago']}/approve",customer)
        assert call('GET',f"/orders/{order['id_pedido']}",customer)['estado']=='CONFIRMADO'
        call('GET','/orders',customer)
        call('GET','/experience/recommendations',customer)
        call('POST','/experience/fitting',customer,{'id_variante':variant['id_variante']})
        reservation = call('POST','/reservations',customer,{'id_inventario':inventory['id_inventario'],'cantidad':1},201)

        assignments = call('GET','/experience/staff',admin)['usuarios']
        changes = []
        try:
            for role, email, password in [('ENCARGADO_SUCURSAL','encargado@vestidor.local','Encargado123!'),('CAJERO','cajero@vestidor.local','Cajero123!')]:
                employee = next(u for u in assignments if u['rol']==role)
                changes.append(employee)
                call('PUT',f"/experience/staff/{employee['id_usuario']}",admin,{'id_sucursal':branch['id_sucursal']})
                token = login(email,password)
                if role=='ENCARGADO_SUCURSAL':
                    call('GET','/admin/inventory',token)
                    assert any(r['id_reserva']==reservation['id_reserva'] for r in call('GET','/reservations',token))
                    call('PUT',f"/reservations/{reservation['id_reserva']}",token,{'estado':'CONFIRMADA'})
                else:
                    options = call('GET','/commerce/pos/options',token)
                    sale = call('POST','/commerce/pos',token,{'id_cliente':options['clientes'][0]['id_cliente'],'metodo_pago':'EFECTIVO','items':[{'id_inventario':inventory['id_inventario'],'cantidad':1}]},201)
                call('POST','/auth/logout',token)
        finally:
            for employee in changes:
                call('PUT',f"/experience/staff/{employee['id_usuario']}",admin,{'id_sucursal':employee['id_sucursal']})
        call('PUT',f"/reservations/{reservation['id_reserva']}",customer,{'estado':'CANCELADA'})
        options = call('GET','/commerce/returns/options',admin)
        detail = next(d for d in options['detalles'] if d['id_pedido']==sale['id_pedido'])
        call('POST','/commerce/returns',admin,{'id_detalle':detail['id_detalle'],'id_inventario':inventory['id_inventario'],'cantidad':1,'motivo':'Prueba de devolución'},201)
        updated = next(i for i in call('GET','/admin/inventory',admin) if i['id_inventario']==inventory['id_inventario'])
        assert updated['stock']==8
        call('GET','/commerce/audit',admin)
        call('GET','/admin/reports/sales',admin)
        reset = call('POST','/auth/request-password-reset',body={'correo':email if False else f'journey-{suffix}@example.com'})
        assert reset.get('token'), 'Enable development reset tokens for this journey'
        call('POST','/auth/reset-password',body={'token':reset['token'],'nueva_password':'Cliente456!'})
        call('GET','/users/profile',customer,expected=401)
        customer = login(f'journey-{suffix}@example.com','Cliente456!')
        call('POST','/auth/logout',customer)
        call('POST','/auth/logout',admin)

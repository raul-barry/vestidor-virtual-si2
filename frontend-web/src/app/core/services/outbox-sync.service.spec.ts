import { of } from 'rxjs';
import { ApiService } from './api.service';
import { TokenService } from './token.service';
import { CatalogOfflineStore } from '../../features/catalog/services/catalog-offline.store';
import { ReservationOfflineStore } from '../../features/reservations/reservation-offline.store';
import { OutboxSyncService } from './outbox-sync.service';

describe('OutboxSyncService sales', () => {
  const tokenKey = 'vestidor_virtual_token';
  const store = new CatalogOfflineStore();
  let api: jasmine.SpyObj<ApiService>;
  let service: OutboxSyncService;

  beforeEach(() => {
    const payload = btoa(JSON.stringify({ id_usuario: 4101, id_organizacion: 4102, exp: Math.floor(Date.now() / 1000) + 3600 }));
    localStorage.setItem(tokenKey, `header.${payload}.signature`);
    api = jasmine.createSpyObj<ApiService>('ApiService', ['post']);
    service = new OutboxSyncService(store, api, new TokenService(), {} as ReservationOfflineStore);
  });

  afterEach(() => localStorage.removeItem(tokenKey));

  it('queues offline cart lines and reconciles a partial result without storing credentials', async () => {
    await service.cacheVariantStock(71, [{ id_inventario: 701, id_variante: 71, disponible: 1, sucursal: 'Central' }]);
    await service.cacheVariantStock(72, [{ id_inventario: 702, id_variante: 72, disponible: 1, sucursal: 'Central' }]);
    let cart = await service.addOfflineCartItem({ id_variante: 71, talla: 'M', color: 'Azul' }, { nombre: 'Camisa', precio_base: '20.00' });
    cart = await service.addOfflineCartItem({ id_variante: 72, talla: 'L', color: 'Negro' }, { nombre: 'Pantalón', precio_base: '30.00' });
    expect((await service.localCart())?.offline_modified).toBeTrue();
    const order = await service.queueOfflineSale(cart, {}, 'EFECTIVO', 60);
    const rows = await store.listOutbox('org:4102', 4101);
    const operation = rows.find(row => row.operation_uuid === order.local_operation_uuid)!;
    expect(operation.payload['lineas']).toHaveSize(2);
    expect(JSON.stringify(operation.payload).toLowerCase()).not.toContain('token');
    expect(await service.localCart()).toEqual({ id_carrito: 0, estado: 'LOCAL', items: [], total: '0.00', offline_modified: false });

    api.post.and.returnValue(of({ results: [{
      operation_uuid: order.local_operation_uuid,
      status: 'SINCRONIZADA',
      result: {
        pedido: { id_pedido: 987, estado: 'PENDIENTE', total: '20.00', metodo_pago: 'EFECTIVO', estado_pago: 'PENDIENTE' },
        lineas_aceptadas: [{ client_line_id: 'variant-71', precio_unitario: '20.00' }],
        lineas_rechazadas: [{ client_line_id: 'variant-72', id_variante: 72, cantidad: 1, motivo: 'CONFLICTO_INVENTARIO' }],
        parcial: true
      }
    }] } as any));

    await Promise.all([service.syncPending(), service.syncPending()]);

    const saved = (await store.listOutbox('org:4102', 4101)).find(row => row.operation_uuid === order.local_operation_uuid)!;
    expect(saved.status).toBe('SINCRONIZADA');
    expect(api.post).toHaveBeenCalledTimes(1);
    const local = (await service.localOrders())[0];
    expect(local.id_pedido).toBe(987);
    expect(local.estado_sync).toBe('PARCIAL');
    expect(local.detalles[1]['estado_sync']).toBe('RECHAZADA');
    expect(await service.cachedVariantStock(72)).toEqual([{ id_inventario: 702, id_variante: 72, disponible: 1, sucursal: 'Central' }]);
  });

  it('queues an offline payment request with tenant scope and no card data', async () => {
    const operation = await service.queuePaymentRequest(123, 'TARJETA');
    expect(operation.operation_type).toBe('pago.solicitar');
    expect(operation.tenant_scope).toBe('org:4102');
    expect(operation.payload).toEqual({
      id_usuario: 4101, id_pedido: 123, metodo_pago: 'TARJETA', datos_pago: {}
    });
    expect(JSON.stringify(operation.payload).toLowerCase()).not.toContain('card');
  });

  it('persists a tenant-scoped cash-only POS sale with its UUID while offline', async () => {
    spyOnProperty(navigator, 'onLine', 'get').and.returnValue(false);
    await service.cachePosOptions({ clientes: [], inventario: [{ id_sucursal: 8, id_variante: 9 }] });
    const queued = await service.queuePosCashSale({
      id_sucursal: 8, id_cliente: null, importe_recibido: 50,
      lineas: [{ id_variante: 9, cantidad: 1 }]
    });
    const stored = (await store.listOutbox('org:4102', 4101)).find(row => row.operation_uuid === queued.operation_uuid)!;
    expect(stored.operation_type).toBe('pos.venta_contado');
    expect(stored.tenant_scope).toBe('org:4102');
    expect(stored.status).toBe('PENDIENTE');
    expect(stored.payload['metodo_pago']).toBeUndefined();
    expect(await service.cachedPosOptions()).toEqual({ clientes: [], inventario: [{ id_sucursal: 8, id_variante: 9 }] });
    expect(api.post).not.toHaveBeenCalled();
  });
});

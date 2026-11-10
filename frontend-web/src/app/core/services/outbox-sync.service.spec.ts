import { of, throwError } from 'rxjs';
import { ApiService } from './api.service';
import { TokenService } from './token.service';
import { CatalogOfflineStore } from '../../features/catalog/services/catalog-offline.store';
import { ReservationOfflineStore } from '../../features/reservations/reservation-offline.store';
import { OutboxSyncService } from './outbox-sync.service';

describe('OutboxSyncService sales', () => {
  const tokenKey = 'vestidor_virtual_token';
  const store = new CatalogOfflineStore();
  let userId: number;
  let organizationId: number;
  let sequence = 0;
  let api: jasmine.SpyObj<ApiService>;
  let service: OutboxSyncService;
  let reservations: jasmine.SpyObj<ReservationOfflineStore>;

  function setOnline(value: boolean): void {
    Object.defineProperty(navigator, 'onLine', { configurable: true, get: () => value });
  }

  beforeEach(async () => {
    setOnline(false);
    userId = 4100 + ++sequence;
    organizationId = 4200 + sequence;
    const payload = btoa(JSON.stringify({ id_usuario: userId, id_organizacion: organizationId, exp: Math.floor(Date.now() / 1000) + 3600 }));
    localStorage.setItem(tokenKey, `header.${payload}.signature`);
    api = jasmine.createSpyObj<ApiService>('ApiService', ['post']);
    reservations = jasmine.createSpyObj<ReservationOfflineStore>('ReservationOfflineStore', ['reconcile']);
    service = new OutboxSyncService(store, api, new TokenService(), reservations);
    await Promise.resolve();
  });

  afterEach(() => {
    localStorage.removeItem(tokenKey);
    setOnline(true);
  });

  it('queues offline cart lines and reconciles a partial result without storing credentials', async () => {
    await service.cacheVariantStock(71, [{ id_inventario: 701, id_variante: 71, disponible: 1, sucursal: 'Central' }]);
    await service.cacheVariantStock(72, [{ id_inventario: 702, id_variante: 72, disponible: 1, sucursal: 'Central' }]);
    let cart = await service.addOfflineCartItem({ id_variante: 71, talla: 'M', color: 'Azul' }, { nombre: 'Camisa', precio_base: '20.00' });
    cart = await service.addOfflineCartItem({ id_variante: 72, talla: 'L', color: 'Negro' }, { nombre: 'Pantalón', precio_base: '30.00' });
    expect((await service.localCart())?.offline_modified).toBeTrue();
    const order = await service.queueOfflineSale(cart, {}, 'EFECTIVO', 60);
    const rows = await store.listOutbox(`org:${organizationId}`, userId);
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

    setOnline(true);
    await Promise.all([service.syncPending(), service.syncPending()]);

    const saved = (await store.listOutbox(`org:${organizationId}`, userId)).find(row => row.operation_uuid === order.local_operation_uuid)!;
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
    expect(operation.tenant_scope).toBe(`org:${organizationId}`);
    expect(operation.payload).toEqual({
      id_usuario: userId, id_pedido: 123, metodo_pago: 'TARJETA', datos_pago: {}
    });
    expect(JSON.stringify(operation.payload).toLowerCase()).not.toContain('card');
  });

  it('persists a tenant-scoped cash-only POS sale with its UUID while offline', async () => {
    setOnline(false);
    await service.cachePosOptions({ clientes: [], inventario: [{ id_sucursal: 8, id_variante: 9 }] });
    const queued = await service.queuePosCashSale({
      id_sucursal: 8, id_cliente: null, importe_recibido: 50,
      lineas: [{ id_variante: 9, cantidad: 1 }]
    });
    const stored = (await store.listOutbox(`org:${organizationId}`, userId)).find(row => row.operation_uuid === queued.operation_uuid)!;
    expect(stored.operation_type).toBe('pos.venta_contado');
    expect(stored.tenant_scope).toBe(`org:${organizationId}`);
    expect(stored.status).toBe('PENDIENTE');
    expect(stored.payload['metodo_pago']).toBeUndefined();
    expect(await service.cachedPosOptions()).toEqual({ clientes: [], inventario: [{ id_sucursal: 8, id_variante: 9 }] });
    expect(api.post).not.toHaveBeenCalled();
  });

  it('serializes reservation and POS outbox rows to the strict backend contract without local metadata', async () => {
    setOnline(true);
    for (const operationType of ['reserva.crear', 'pos.venta_contado']) {
      const operation = await service.enqueue(operationType, operationType === 'reserva.crear'
        ? { id_inventario: 31, cantidad: 1, id_usuario: userId }
        : { id_sucursal: 8, importe_recibido: 25, lineas: [{ id_variante: 9, cantidad: 1 }] });
      api.post.and.returnValue(of({ results: [{ operation_uuid: operation.operation_uuid, status: 'SINCRONIZADA', result: {} }] } as any));

      await service.syncPending();

      const request = api.post.calls.mostRecent().args[1] as { operations: Array<Record<string, unknown>> };
      const sent = request.operations.find(row => row['operation_uuid'] === operation.operation_uuid)!;
      expect(sent).toBeDefined();
      expect(sent['owner_user_id']).toBeUndefined();
      expect(Object.keys(sent).sort()).toEqual([
        'client_id', 'created_at', 'operation_type', 'operation_uuid', 'payload', 'schema_version', 'tenant_scope'
      ]);
      expect((await store.listOutbox(`org:${organizationId}`, userId)).find(row => row.operation_uuid === operation.operation_uuid)?.status).toBe('SINCRONIZADA');
    }
  });

  it('preserves server validation details and does not resubmit rejected operations', async () => {
    setOnline(true);
    const operation = await service.enqueue('reserva.crear', { id_inventario: 'invalid', cantidad: 1, id_usuario: userId });
    api.post.and.returnValue(throwError(() => ({ status: 422, error: { detail: [
      { loc: ['body', 'operations', 0, 'owner_user_id'], msg: 'Extra inputs are not permitted' }
    ] } })));

    await service.syncPending();
    const rejected = (await store.listOutbox(`org:${organizationId}`, userId)).find(row => row.operation_uuid === operation.operation_uuid)!;
    expect(rejected.status).toBe('RECHAZADA');
    expect(rejected.error_category).toBe('DATOS_INVALIDOS');
    expect(rejected.error_message).toBe('operations.0.owner_user_id: Extra inputs are not permitted');

    await service.syncPending();
    expect(api.post).toHaveBeenCalledTimes(1);
  });

  it('keeps transport failures retryable and retries only when explicitly requested', async () => {
    setOnline(false);
    const operation = await service.enqueue('reserva.crear', { id_inventario: 31, cantidad: 1, id_usuario: userId });
    api.post.and.returnValue(throwError(() => ({ status: 0, message: 'network unavailable' })));

    // A real request failure is marked retryable; an offline client never sends it again automatically.
    setOnline(true);
    await service.syncPending();
    const retryable = (await store.listOutbox(`org:${organizationId}`, userId)).find(row => row.operation_uuid === operation.operation_uuid)!;
    expect(retryable.status).toBe('ERROR_REINTENTABLE');
    setOnline(false);
    expect(await service.retryOperation(operation.operation_uuid)).toBeTrue();
    const pending = (await store.listOutbox(`org:${organizationId}`, userId)).find(row => row.operation_uuid === operation.operation_uuid)!;
    expect(pending.status).toBe('PENDIENTE');
  });
});

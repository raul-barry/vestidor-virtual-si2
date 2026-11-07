import { CatalogOfflineStore } from './catalog-offline.store';

describe('CatalogOfflineStore outbox', () => {
  const store = new CatalogOfflineStore();
  const scopeA = `org:test-a-${crypto.randomUUID()}`;
  const scopeB = `org:test-b-${crypto.randomUUID()}`;

  it('persists operations by tenant and atomically claims pending work once', async () => {
    const item = await store.enqueue({
      operation_uuid: crypto.randomUUID(), operation_type: 'demo.noop', payload: { ref: 1 },
      created_at: new Date().toISOString(), schema_version: 1, client_id: 'browser-test', tenant_scope: scopeA
    });
    await store.enqueue({
      operation_uuid: crypto.randomUUID(), operation_type: 'demo.noop', payload: { ref: 2 },
      created_at: new Date().toISOString(), schema_version: 1, client_id: 'browser-test', tenant_scope: scopeB
    });

    const [claimOne, claimTwo] = await Promise.all([store.claimPending(scopeA), store.claimPending(scopeA)]);
    expect([...claimOne, ...claimTwo].map(row => row.operation_uuid)).toEqual([item.operation_uuid]);
    expect((await store.listOutbox(scopeB)).map(row => row.tenant_scope)).toEqual([scopeB]);
    expect((await store.listOutbox(scopeA))[0].status).toBe('ENVIANDO');
    expect(await store.claimPending(scopeA)).toEqual([]);
  });

  it('rejects credential fields and records tenant-scoped last synchronization', async () => {
    await expectAsync(store.enqueue({
      operation_uuid: crypto.randomUUID(), operation_type: 'demo.noop', payload: { password: 'do-not-store' },
      created_at: new Date().toISOString(), schema_version: 1, client_id: 'browser-test', tenant_scope: scopeA
    })).toBeRejected();

    await store.setLastSync(scopeA, 1234);
    expect(await store.getLastSync(scopeA)).toBe(1234);
    expect(await store.getLastSync(scopeB)).toBeNull();
  });

  it('stores offline carts and orders independently for each organization and user', async () => {
    const order = { local_operation_uuid: crypto.randomUUID(), estado_sync: 'PENDIENTE', total: '50.00' };
    await store.putSalesData(scopeA, 41, 'cart', { items: [{ id_variante: 7, cantidad: 1 }] });
    await store.putSalesData(scopeA, 41, 'orders', [order]);
    await store.putSalesData(scopeB, 41, 'cart', { items: [] });

    expect(await store.getSalesData(scopeA, 41, 'cart')).toEqual({ items: [{ id_variante: 7, cantidad: 1 }] });
    expect(await store.getSalesData(scopeB, 41, 'orders')).toBeNull();
    expect(await store.getSalesData(scopeA, 42, 'orders')).toBeNull();
  });
});

import { OutboxOperation } from '../catalog/services/catalog-offline.store';
import { ReservationOfflineStore } from './reservation-offline.store';

describe('ReservationOfflineStore', () => {
  const store = new ReservationOfflineStore();
  const scope = `org:reservation-test-${crypto.randomUUID()}`;

  it('keeps reservation and availability snapshots isolated by tenant and user', async () => {
    await store.saveReservations(scope, 11, [{ id_reserva: 5, estado: 'PENDIENTE' }]);
    await store.saveReservations(scope, 12, [{ id_reserva: 6, estado: 'PENDIENTE' }]);
    await store.saveAvailability(scope, 11, [{ id_inventario: 1, disponible: 3 }]);

    expect((await store.readReservations(scope, 11))[0].id_reserva).toBe(5);
    expect((await store.readReservations(scope, 12))[0].id_reserva).toBe(6);
    expect(await store.readAvailability(scope, 12)).toEqual([]);
  });

  it('restores provisional availability when the server rejects a pending reservation', async () => {
    await store.saveAvailability(scope, 13, [{ id_inventario: 22, disponible: 0 }]);
    await store.saveReservations(scope, 13, [{
      id_reserva: 0, id_inventario: 22, cantidad: 2, estado: 'PENDIENTE',
      local_operation_uuid: 'operation-22', sync_status: 'PENDIENTE'
    }]);
    const operation: OutboxOperation = {
      operation_uuid: 'operation-22', operation_type: 'reserva.crear',
      payload: { id_usuario: 13, id_inventario: 22, cantidad: 2 },
      created_at: new Date().toISOString(), schema_version: 1, client_id: 'test-device',
      tenant_scope: scope, owner_user_id: 13, status: 'RECHAZADA', attempts: 1, updated_at: Date.now()
    };

    await store.reconcile(operation, { operation_uuid: operation.operation_uuid,
      status: 'RECHAZADA', category: 'CONFLICTO_INVENTARIO', message: 'Disponibilidad insuficiente.' });

    expect((await store.readAvailability(scope, 13))[0].disponible).toBe(2);
    const rejected = (await store.readReservations(scope, 13))[0];
    expect(rejected.estado).toBe('RECHAZADA');
    expect(rejected.sync_status).toBe('RECHAZADA');
    expect(rejected.sync_message).toBe('Disponibilidad insuficiente.');
  });
});

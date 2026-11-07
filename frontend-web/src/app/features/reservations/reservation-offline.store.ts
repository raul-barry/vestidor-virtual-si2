import { Injectable } from '@angular/core';
import { OutboxOperation, OutboxStatus } from '../catalog/services/catalog-offline.store';

export interface ReservationSyncItem {
  operation_uuid: string;
  status: OutboxStatus;
  category?: string;
  message?: string;
  result?: Record<string, unknown>;
}

@Injectable({ providedIn: 'root' })
export class ReservationOfflineStore {
  private database?: Promise<IDBDatabase>;
  private open(): Promise<IDBDatabase> {
    return this.database ??= new Promise((resolve, reject) => {
      const request = indexedDB.open('fashion-store-offline-reservations', 1);
      request.onupgradeneeded = () => request.result.createObjectStore('snapshots', { keyPath: 'key' });
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  private async read(key: string): Promise<any[]> {
    const db = await this.open();
    return new Promise((resolve, reject) => {
      const request = db.transaction('snapshots').objectStore('snapshots').get(key);
      request.onsuccess = () => resolve(request.result?.values ?? []);
      request.onerror = () => reject(request.error);
    });
  }

  private async write(key: string, values: any[]): Promise<void> {
    const db = await this.open();
    await new Promise<void>((resolve, reject) => {
      const request = db.transaction('snapshots', 'readwrite').objectStore('snapshots').put({ key, values, updated_at: Date.now() });
      request.onsuccess = () => resolve(); request.onerror = () => reject(request.error);
    });
  }

  reservationsKey(scope: string, userId: number): string { return `reservations:${scope}:${userId}`; }
  availabilityKey(scope: string, userId: number): string { return `availability:${scope}:${userId}`; }
  readReservations(scope: string, userId: number): Promise<any[]> { return this.read(this.reservationsKey(scope, userId)); }
  saveReservations(scope: string, userId: number, values: any[]): Promise<void> { return this.write(this.reservationsKey(scope, userId), values); }
  readAvailability(scope: string, userId: number): Promise<any[]> { return this.read(this.availabilityKey(scope, userId)); }
  saveAvailability(scope: string, userId: number, values: any[]): Promise<void> { return this.write(this.availabilityKey(scope, userId), values); }

  async reconcile(operation: OutboxOperation, item: ReservationSyncItem): Promise<void> {
    const userId = Number(operation.payload['id_usuario']);
    if (!Number.isInteger(userId) || userId < 1) return;
    const reservationsKey = this.reservationsKey(operation.tenant_scope, userId);
    const reservations = await this.read(reservationsKey);
    const availability = await this.read(this.availabilityKey(operation.tenant_scope, userId));
    const payload = operation.payload;
    const reservationIndex = reservations.findIndex(row =>
      operation.operation_type === 'reserva.crear'
        ? row.local_operation_uuid === operation.operation_uuid
        : Number(row.id_reserva) === Number(payload['id_reserva']));
    const row = reservationIndex >= 0 ? reservations[reservationIndex] : undefined;
    const inventoryId = Number(payload['id_inventario'] ?? row?.id_inventario);
    const quantity = Number(payload['cantidad'] ?? row?.cantidad ?? 0);
    const inv = availability.find(item => Number(item['id_inventario']) === inventoryId);

    if (operation.operation_type === 'reserva.crear') {
      if (item.status === 'SINCRONIZADA' && row) {
        reservations[reservationIndex] = { ...row, ...(item.result ?? {}), local_operation_uuid: undefined, estado: item.result?.['estado'] ?? 'PENDIENTE', sync_status: item.status };
      } else if (item.status === 'RECHAZADA') {
        if (row) { row.estado = 'RECHAZADA'; row.sync_status = item.status; row.sync_message = item.message ?? 'Reserva rechazada por el servidor.'; }
        if (inv) inv['disponible'] = Number(inv['disponible']) + quantity;
      } else if (row) {
        row.sync_status = item.status; row.sync_message = item.message ?? 'Reserva registrada. Esperando confirmación del servidor';
      }
    } else if (operation.operation_type === 'reserva.cancelar' && row) {
      if (item.status === 'SINCRONIZADA') {
        row.estado = 'CANCELADA'; row.sync_status = item.status; row.local_cancel_operation_uuid = undefined;
      } else if (item.status === 'RECHAZADA') {
        row.estado = String(payload['estado_anterior'] ?? 'PENDIENTE'); row.sync_status = item.status;
        row.local_cancel_operation_uuid = undefined;
        if (inv) inv['disponible'] = Math.max(0, Number(inv['disponible']) - quantity);
      } else {
        row.sync_status = item.status; row.sync_message = item.message;
      }
    }
    await Promise.all([this.write(reservationsKey, reservations), this.write(this.availabilityKey(operation.tenant_scope, userId), availability)]);
  }
}

import { Injectable } from '@angular/core';
import { Producto } from '../../../shared/models/producto.model';

interface Snapshot { key: string; products: Producto[]; syncedAt: number; }
export type OutboxStatus = 'PENDIENTE' | 'ENVIANDO' | 'SINCRONIZADA' | 'RECHAZADA' | 'ERROR_REINTENTABLE';
export interface OutboxOperation {
  operation_uuid: string; operation_type: string; payload: Record<string, unknown>; created_at: string;
  schema_version: number; client_id: string; tenant_scope: string; owner_user_id?: number; status: OutboxStatus;
  attempts: number; error_category?: string; error_message?: string; updated_at: number;
  result?: Record<string, unknown>;
}

const forbiddenCredentialKey = /^(authorization|access_token|refresh_token|token|password|password_hash|secret|cvv|card_number|numero_tarjeta)$/i;
function containsCredential(value: unknown): boolean {
  if (Array.isArray(value)) return value.some(containsCredential);
  return !!value && typeof value === 'object' && Object.entries(value).some(
    ([key, child]) => forbiddenCredentialKey.test(key) || containsCredential(child)
  );
}

@Injectable({ providedIn: 'root' })
export class CatalogOfflineStore {
  private db?: Promise<IDBDatabase>;
  private open(): Promise<IDBDatabase> {
    if (!('indexedDB' in globalThis)) return Promise.reject(new Error('IndexedDB no disponible'));
    return this.db ??= new Promise((resolve, reject) => {
      const request = indexedDB.open('fashion-store-public-catalog', 4);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains('snapshots')) db.createObjectStore('snapshots', { keyPath: 'key' });
        if (!db.objectStoreNames.contains('outbox')) {
          const outbox = db.createObjectStore('outbox', { keyPath: 'operation_uuid' });
          outbox.createIndex('tenant_scope', 'tenant_scope');
          outbox.createIndex('tenant_status', ['tenant_scope', 'status']);
        }
        const outbox = request.transaction!.objectStore('outbox');
        if (!outbox.indexNames.contains('tenant_owner_status')) outbox.createIndex('tenant_owner_status', ['tenant_scope', 'owner_user_id', 'status']);
        if (!db.objectStoreNames.contains('sync_metadata')) db.createObjectStore('sync_metadata', { keyPath: 'tenant_scope' });
        if (!db.objectStoreNames.contains('sales')) db.createObjectStore('sales', { keyPath: 'key' });
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }
  async get(key: string): Promise<Snapshot | null> {
    const db = await this.open();
    return new Promise((resolve, reject) => {
      const request = db.transaction('snapshots').objectStore('snapshots').get(key);
      request.onsuccess = () => resolve(request.result ?? null);
      request.onerror = () => reject(request.error);
    });
  }
  async put(snapshot: Snapshot): Promise<void> {
    const db = await this.open();
    return new Promise<void>((resolve, reject) => {
      const request = db.transaction('snapshots', 'readwrite').objectStore('snapshots').put(snapshot);
      request.onsuccess = () => resolve(); request.onerror = () => reject(request.error);
    });
  }

  async enqueue(operation: Omit<OutboxOperation, 'status' | 'attempts' | 'updated_at'>): Promise<OutboxOperation> {
    if (containsCredential(operation.payload)) throw new Error('La operaciÃ³n contiene credenciales que no se guardan en Outbox.');
    const row: OutboxOperation = { ...operation, status: 'PENDIENTE', attempts: 0, updated_at: Date.now() };
    const db = await this.open();
    await new Promise<void>((resolve, reject) => {
      const request = db.transaction('outbox', 'readwrite').objectStore('outbox').add(row);
      request.onsuccess = () => resolve(); request.onerror = () => reject(request.error);
    });
    return row;
  }

  async listOutbox(scope: string, ownerUserId?: number): Promise<OutboxOperation[]> {
    const db = await this.open();
    return new Promise((resolve, reject) => {
      const request = db.transaction('outbox').objectStore('outbox').index('tenant_scope').getAll(scope);
      request.onsuccess = () => resolve((request.result as OutboxOperation[])
        .filter(row => ownerUserId === undefined || row.owner_user_id === ownerUserId)
        .sort((a, b) => a.created_at.localeCompare(b.created_at)));
      request.onerror = () => reject(request.error);
    });
  }

  async claimPending(scope: string, limit = 50, ownerUserId?: number): Promise<OutboxOperation[]> {
    const db = await this.open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction('outbox', 'readwrite');
      const index = tx.objectStore('outbox').index(ownerUserId === undefined ? 'tenant_status' : 'tenant_owner_status');
      const selected: OutboxOperation[] = [];
      let remaining = 2;
      for (const status of ['PENDIENTE', 'ERROR_REINTENTABLE']) {
        const request = index.getAll(IDBKeyRange.only(ownerUserId === undefined ? [scope, status] : [scope, ownerUserId, status]));
        request.onsuccess = () => {
          for (const row of request.result as OutboxOperation[]) {
            if (selected.length >= limit) break;
            row.status = 'ENVIANDO'; row.attempts += 1; row.updated_at = Date.now();
            selected.push(row);
          }
          if (--remaining === 0) {
            const store = tx.objectStore('outbox');
            for (const row of selected) store.put(row);
          }
        };
        request.onerror = () => { try { tx.abort(); } catch {} reject(request.error); };
      }
      tx.oncomplete = () => resolve(selected);
      tx.onerror = () => reject(tx.error);
      tx.onabort = () => reject(tx.error);
    });
  }

  async recoverStale(scope: string, staleAfterMs = 5 * 60_000): Promise<void> {
    const db = await this.open();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction('outbox', 'readwrite');
      const store = tx.objectStore('outbox');
      const request = store.index('tenant_scope').getAll(scope);
      request.onsuccess = () => {
        const cutoff = Date.now() - staleAfterMs;
        for (const row of request.result as OutboxOperation[]) {
          if (row.status === 'ENVIANDO' && row.updated_at < cutoff) {
            store.put({ ...row, status: 'ERROR_REINTENTABLE', error_category: 'TEMPORAL', error_message: 'Se reanudará un envío interrumpido.', updated_at: Date.now() });
          }
        }
      };
      request.onerror = () => reject(request.error);
      tx.oncomplete = () => resolve(); tx.onerror = () => reject(tx.error); tx.onabort = () => reject(tx.error);
    });
  }

  async updateOutbox(operation: OutboxOperation): Promise<void> {
    const db = await this.open();
    await new Promise<void>((resolve, reject) => {
      const request = db.transaction('outbox', 'readwrite').objectStore('outbox').put({ ...operation, updated_at: Date.now() });
      request.onsuccess = () => resolve(); request.onerror = () => reject(request.error);
    });
  }

  async deletePending(operationUuid: string): Promise<boolean> {
    const db = await this.open();
    return new Promise<boolean>((resolve, reject) => {
      const tx = db.transaction('outbox', 'readwrite');
      const store = tx.objectStore('outbox');
      let deleted = false;
      const request = store.get(operationUuid);
      request.onsuccess = () => {
        const row = request.result as OutboxOperation | undefined;
        if (row && (row.status === 'PENDIENTE' || row.status === 'ERROR_REINTENTABLE')) { store.delete(operationUuid); deleted = true; }
      };
      request.onerror = () => reject(request.error);
      tx.oncomplete = () => resolve(deleted); tx.onerror = () => reject(tx.error); tx.onabort = () => reject(tx.error);
    });
  }

  async setLastSync(scope: string, syncedAt = Date.now()): Promise<void> {
    const db = await this.open();
    await new Promise<void>((resolve, reject) => {
      const request = db.transaction('sync_metadata', 'readwrite').objectStore('sync_metadata').put({ tenant_scope: scope, synced_at: syncedAt });
      request.onsuccess = () => resolve(); request.onerror = () => reject(request.error);
    });
  }

  async getLastSync(scope: string): Promise<number | null> {
    const db = await this.open();
    return new Promise((resolve, reject) => {
      const request = db.transaction('sync_metadata').objectStore('sync_metadata').get(scope);
      request.onsuccess = () => resolve(request.result?.synced_at ?? null);
      request.onerror = () => reject(request.error);
    });
  }

  async getSalesData<T>(scope: string, ownerUserId: number, kind: string): Promise<T | null> {
    const db = await this.open();
    return new Promise((resolve, reject) => {
      const request = db.transaction('sales').objectStore('sales').get(`${scope}:${ownerUserId}:${kind}`);
      request.onsuccess = () => resolve((request.result?.value as T | undefined) ?? null);
      request.onerror = () => reject(request.error);
    });
  }

  async putSalesData(scope: string, ownerUserId: number, kind: string, value: unknown): Promise<void> {
    const db = await this.open();
    await new Promise<void>((resolve, reject) => {
      const request = db.transaction('sales', 'readwrite').objectStore('sales').put({
        key: `${scope}:${ownerUserId}:${kind}`, scope, owner_user_id: ownerUserId, kind, value, updated_at: Date.now()
      });
      request.onsuccess = () => resolve(); request.onerror = () => reject(request.error);
    });
  }
}

import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { ApiService } from './api.service';
import { TokenService } from './token.service';
import { CatalogOfflineStore, OutboxOperation, OutboxStatus } from '../../features/catalog/services/catalog-offline.store';
import { ReservationOfflineStore } from '../../features/reservations/reservation-offline.store';

export interface OutboxSummary {
  pending: number; sending: number; synchronized: number; rejected: number; retryable: number;
  lastSync: number | null; online: boolean; errors: OutboxOperation[];
}
export interface OfflineSaleOrder {
  id_pedido?: number | null; local_operation_uuid: string; numero_local: string; fecha_pedido: string;
  estado: string; estado_sync: string; total: string; metodo_pago: 'EFECTIVO' | 'TARJETA' | 'QR';
  estado_pago: string; mensaje_sync: string; detalles: Array<Record<string, any>>; [key: string]: any;
}

const forbidden = /^(authorization|access_token|refresh_token|token|password|password_hash|secret|cvv|card_number|numero_tarjeta)$/i;
function containsCredential(value: unknown): boolean {
  if (Array.isArray(value)) return value.some(containsCredential);
  if (value && typeof value === 'object') return Object.entries(value).some(([key, child]) => forbidden.test(key) || containsCredential(child));
  return false;
}

@Injectable({ providedIn: 'root' })
export class OutboxSyncService {
  private syncing = false;
  private readonly state = new BehaviorSubject<OutboxSummary>({ pending: 0, sending: 0, synchronized: 0, rejected: 0, retryable: 0, lastSync: null, online: navigator.onLine, errors: [] });
  readonly summary$ = this.state.asObservable();
  private readonly connectionChanged = (): void => {
    void this.refresh();
    if (navigator.onLine) void this.syncPending();
  };

  constructor(private readonly store: CatalogOfflineStore, private readonly api: ApiService, private readonly tokens: TokenService,
              private readonly reservations: ReservationOfflineStore) {
    window.addEventListener('online', this.connectionChanged);
    window.addEventListener('offline', this.connectionChanged);
    queueMicrotask(() => { void this.refresh(); if (navigator.onLine) void this.syncPending(); });
  }

  async enqueue(operationType: string, payload: Record<string, unknown>, schemaVersion = 1): Promise<OutboxOperation> {
    const organizationId = this.tokens.getOrganizationId();
    const userId = this.tokens.getUserId();
    if (!this.tokens.hasToken() || organizationId === null) throw new Error('Se requiere una sesión autenticada con organización.');
    if (containsCredential(payload)) throw new Error('La operación contiene credenciales o datos de pago que no se guardan en Outbox.');
    if (userId === null) throw new Error('La sesión no contiene un usuario válido.');
    const row = await this.store.enqueue({
      operation_uuid: crypto.randomUUID(), operation_type: operationType, payload,
      created_at: new Date().toISOString(), schema_version: schemaVersion,
      client_id: this.clientId(), tenant_scope: `org:${organizationId}`, owner_user_id: userId
    });
    await this.refresh();
    return row;
  }

  async removeUnsent(operationUuid: string): Promise<boolean> {
    const scope = this.scope();
    const owner = this.tokens.getUserId();
    if (!scope || owner === null) return false;
    const row = (await this.store.listOutbox(scope, owner)).find(item => item.operation_uuid === operationUuid);
    if (!row || !['PENDIENTE', 'ERROR_REINTENTABLE'].includes(row.status)) return false;
    if (!await this.store.deletePending(operationUuid)) return false;
    await this.refresh();
    return true;
  }

  async localCart(): Promise<any | null> {
    const scope = this.scope(); const owner = this.tokens.getUserId();
    return scope && owner !== null ? this.store.getSalesData<any>(scope, owner, 'cart') : null;
  }

  async saveLocalCart(cart: any, offlineModified = false): Promise<void> {
    const scope = this.scope(); const owner = this.tokens.getUserId();
    if (scope && owner !== null) {
      await this.store.putSalesData(scope, owner, 'cart', { ...cart, offline_modified: offlineModified });
    }
  }

  isOfflineModifiedCart(cart: any | null): boolean {
    return !!cart?.offline_modified;
  }

  async cacheVariantStock(variantId: number, rows: any[]): Promise<void> {
    const scope = this.scope(); const owner = this.tokens.getUserId();
    if (scope && owner !== null) await this.store.putSalesData(scope, owner, `stock:${variantId}`, rows);
  }

  async cachePosOptions(options: Record<string, unknown>): Promise<void> {
    const scope = this.scope(); const owner = this.tokens.getUserId();
    if (scope && owner !== null) await this.store.putSalesData(scope, owner, 'pos-options', options);
  }

  async cachedPosOptions(): Promise<Record<string, any> | null> {
    const scope = this.scope(); const owner = this.tokens.getUserId();
    return scope && owner !== null ? await this.store.getSalesData<Record<string, any>>(scope, owner, 'pos-options') : null;
  }

  async queuePosCashSale(payload: Record<string, unknown>): Promise<OutboxOperation> {
    const operation = await this.enqueue('pos.venta_contado', payload);
    if (navigator.onLine) {
      await this.syncPending();
      const scope = this.scope(); const owner = this.tokens.getUserId();
      if (scope && owner !== null) return (await this.store.listOutbox(scope, owner)).find(row => row.operation_uuid === operation.operation_uuid) ?? operation;
    }
    return operation;
  }

  async cachedVariantStock(variantId: number): Promise<any[]> {
    const scope = this.scope(); const owner = this.tokens.getUserId();
    return scope && owner !== null ? await this.store.getSalesData<any[]>(scope, owner, `stock:${variantId}`) ?? [] : [];
  }

  async cachedExchanges(): Promise<any[]> {
    const scope = this.scope(); const owner = this.tokens.getUserId();
    return scope && owner !== null ? await this.store.getSalesData<any[]>(scope, owner, 'exchanges') ?? [] : [];
  }

  async cacheExchanges(rows: any[]): Promise<void> {
    const scope = this.scope(); const owner = this.tokens.getUserId();
    if (scope && owner !== null) await this.store.putSalesData(scope, owner, 'exchanges', rows);
  }

  async queuePhysicalExchange(exchange: any, physical: Record<string, unknown>): Promise<OutboxOperation> {
    const userId = this.tokens.getUserId();
    if (userId === null) throw new Error('La sesión no tiene un usuario válido.');
    const operation = await this.enqueue('cambio.registrar_offline', { ...physical, id_usuario: userId, exchange_id: exchange.id });
    const rows = await this.cachedExchanges();
    const index = rows.findIndex(row => row.id === exchange.id);
    const local = { ...exchange, ...physical, local_operation_uuid: operation.operation_uuid,
      sync_status: 'PENDIENTE', state: 'ENTREGA_FISICA_PENDIENTE_DE_SYNC' };
    if (index >= 0) rows[index] = local; else rows.unshift(local);
    await this.cacheExchanges(rows);
    return operation;
  }

  async addOfflineCartItem(variant: { id_variante: number; talla: string; color: string }, product: any, quantity = 1): Promise<any> {
    const scope = this.scope(); const owner = this.tokens.getUserId();
    if (!scope || owner === null || !this.tokens.hasToken()) throw new Error('Se requiere una sesión autenticada para comprar offline.');
    const cart = await this.localCart() ?? { id_carrito: 0, estado: 'LOCAL', items: [], total: '0.00' };
    const stock = await this.store.getSalesData<any[]>(scope, owner, `stock:${variant.id_variante}`) ?? [];
    let remaining = quantity;
    const allocations: Array<{id_inventario: number; cantidad: number}> = [];
    for (const row of [...stock].sort((a, b) => Number(a.id_inventario) - Number(b.id_inventario))) {
      if (remaining <= 0) break;
      const take = Math.min(remaining, Math.max(0, Number(row.disponible) || 0));
      if (take > 0) {
        row.disponible -= take;
        allocations.push({ id_inventario: Number(row.id_inventario), cantidad: take });
        remaining -= take;
      }
    }
    const item = cart.items.find((value: any) => Number(value.id_variante) === variant.id_variante);
    if (item) { item.cantidad += quantity; item.offline_allocations = [...(item.offline_allocations ?? []), ...allocations]; }
    else cart.items.push({
      id_detalle: -Date.now(), id_variante: variant.id_variante, client_line_id: `variant-${variant.id_variante}`,
      producto: product.nombre, talla: variant.talla, color: variant.color, cantidad: quantity,
      precio_unitario: String(product.precio_base), offline_allocations: allocations
    });
    cart.total = cart.items.reduce((sum: number, value: any) => sum + Number(value.precio_unitario) * Number(value.cantidad), 0).toFixed(2);
    await this.store.putSalesData(scope, owner, `stock:${variant.id_variante}`, stock);
    await this.saveLocalCart(cart, true);
    return cart;
  }

  async updateOfflineCartItem(idDetalle: number, cantidad: number | null): Promise<any> {
    const scope = this.scope(); const owner = this.tokens.getUserId();
    if (!scope || owner === null) throw new Error('La organización activa no está disponible.');
    const cart = await this.localCart() ?? { id_carrito: 0, estado: 'LOCAL', items: [], total: '0.00' };
    const index = cart.items.findIndex((value: any) => value.id_detalle === idDetalle);
    if (index < 0) return cart;
    const item = cart.items[index];
    const stock = await this.store.getSalesData<any[]>(scope, owner, `stock:${item.id_variante}`) ?? [];
    let allocations = [...(item.offline_allocations ?? [])];
    const delta = (cantidad ?? 0) - Number(item.cantidad);
    if (delta > 0) {
      let remaining = delta;
      for (const row of [...stock].sort((a, b) => Number(a.id_inventario) - Number(b.id_inventario))) {
        const take = Math.min(remaining, Math.max(0, Number(row.disponible) || 0));
        if (take) {
          row.disponible -= take;
          const allocation = allocations.find((value: any) => value.id_inventario === row.id_inventario);
          if (allocation) allocation.cantidad += take; else allocations.push({ id_inventario: row.id_inventario, cantidad: take });
          remaining -= take;
        }
        if (!remaining) break;
      }
    } else if (delta < 0) {
      let remaining = -delta;
      for (const allocation of [...allocations].reverse()) {
        const restore = Math.min(remaining, Number(allocation.cantidad));
        const row = stock.find((value: any) => value.id_inventario === allocation.id_inventario);
        if (row) row.disponible += restore;
        allocation.cantidad -= restore; remaining -= restore;
        if (!remaining) break;
      }
      allocations = allocations.filter((value: any) => value.cantidad > 0);
    }
    if (cantidad === null || cantidad <= 0) cart.items.splice(index, 1);
    else { item.cantidad = cantidad; item.offline_allocations = allocations; }
    cart.total = cart.items.reduce((sum: number, value: any) => sum + Number(value.precio_unitario) * Number(value.cantidad), 0).toFixed(2);
    await this.store.putSalesData(scope, owner, `stock:${item.id_variante}`, stock);
    await this.saveLocalCart(cart, true);
    return cart;
  }

  async localOrders(): Promise<OfflineSaleOrder[]> {
    const scope = this.scope(); const owner = this.tokens.getUserId();
    return scope && owner !== null ? (await this.store.getSalesData<OfflineSaleOrder[]>(scope, owner, 'orders') ?? []) : [];
  }

  async queueOfflineSale(cart: any, delivery: Record<string, unknown>, method: 'EFECTIVO' | 'TARJETA' | 'QR', received?: number): Promise<OfflineSaleOrder> {
    const owner = this.tokens.getUserId(); const scope = this.scope();
    if (owner === null || !scope || !cart.items?.length) throw new Error('No hay una compra válida para guardar offline.');
    if (cart.items.some((item: any) => !Number.isInteger(item.id_variante) || item.id_variante < 1)) throw new Error('El carrito guardado no contiene identificadores de variante. Vuelve a cargarlo con conexión antes de continuar.');
    if (method === 'EFECTIVO' && (!Number.isFinite(received) || Number(received) < Number(cart.total))) throw new Error('El importe recibido debe cubrir el total provisional.');
    const operation = await this.enqueue('venta.crear', {
      id_usuario: owner, metodo_pago: method, entrega: delivery,
      datos_pago: {
        ...(received === undefined ? {} : { importe_recibido: received.toFixed(2) }),
        ...(method === 'TARJETA' ? { resultado_local: 'PENDIENTE_CONFIRMACION_SERVIDOR' } : {}),
        ...(method === 'QR' ? { verificacion: 'PENDIENTE' } : {})
      },
      lineas: cart.items.map((item: any) => ({
        client_line_id: item.client_line_id ?? `variant-${item.id_variante}`,
        id_variante: item.id_variante, cantidad: item.cantidad,
        ...(item.offline_allocations ? { offline_allocations: item.offline_allocations } : {})
      }))
    });
    const orders = await this.localOrders();
    const local: OfflineSaleOrder = {
      local_operation_uuid: operation.operation_uuid, numero_local: operation.operation_uuid.slice(0, 8).toUpperCase(),
      fecha_pedido: operation.created_at, estado: 'PENDIENTE_SINCRONIZAR', estado_sync: 'PENDIENTE',
      total: String(cart.total), metodo_pago: method, estado_pago: 'PENDIENTE',
      mensaje_sync: 'Venta registrada. Esperando confirmación',
      detalles: cart.items.map((item: any) => ({ ...item, estado_sync: 'PENDIENTE' }))
    };
    orders.unshift(local);
    await this.store.putSalesData(scope, owner, 'orders', orders);
    await this.saveLocalCart({ id_carrito: 0, estado: 'LOCAL', items: [], total: '0.00' });
    await this.refresh();
    return local;
  }

  async queuePaymentRequest(orderId: number, method: 'EFECTIVO' | 'TARJETA' | 'QR'): Promise<OutboxOperation> {
    const userId = this.tokens.getUserId();
    if (!Number.isInteger(orderId) || orderId < 1 || userId === null) {
      throw new Error('No se pudo validar el pedido y el usuario activo.');
    }
    return this.enqueue('pago.solicitar', {
      id_usuario: userId, id_pedido: orderId, metodo_pago: method, datos_pago: {}
    });
  }

  private clientId(): string {
    const key = 'fashion_store_outbox_client_id';
    let value = localStorage.getItem(key);
    if (!value) { value = crypto.randomUUID(); localStorage.setItem(key, value); }
    return value;
  }

  private scope(): string | null {
    const id = this.tokens.getOrganizationId();
    return this.tokens.hasToken() && id !== null ? `org:${id}` : null;
  }

  async refresh(): Promise<OutboxSummary> {
    const scope = this.scope();
    const owner = this.tokens.getUserId();
    const rows = scope && owner !== null ? await this.store.listOutbox(scope, owner) : [];
    const summary: OutboxSummary = {
      pending: rows.filter(row => row.status === 'PENDIENTE').length,
      sending: rows.filter(row => row.status === 'ENVIANDO').length,
      synchronized: rows.filter(row => row.status === 'SINCRONIZADA').length,
      rejected: rows.filter(row => row.status === 'RECHAZADA').length,
      retryable: rows.filter(row => row.status === 'ERROR_REINTENTABLE').length,
      lastSync: scope ? await this.store.getLastSync(scope) : null,
      online: navigator.onLine,
      errors: rows.filter(row => row.status === 'RECHAZADA' || row.status === 'ERROR_REINTENTABLE')
    };
    this.state.next(summary);
    return summary;
  }

  async syncPending(): Promise<void> {
    const scope = this.scope();
    const owner = this.tokens.getUserId();
    if (this.syncing || !navigator.onLine || !scope || owner === null) return;
    this.syncing = true;
    try {
      await this.store.recoverStale(scope);
      const rows = await this.store.claimPending(scope, 50, owner);
      if (!rows.length) return;
      try {
        const response = await this.api.post<{ results: Array<Record<string, unknown>> }>('/api/sync/batch', {
          operations: rows.map(({ status: _status, attempts: _attempts, error_category: _category, error_message: _message, updated_at: _updated, result: _result, ...wire }) => wire)
        }).toPromise();
        await this.applyResults(rows, response?.results ?? [], scope);
        await this.store.setLastSync(scope);
      } catch (error: any) {
        const results = error?.error?.results as Array<Record<string, unknown>> | undefined;
        if (results) {
          await this.applyResults(rows, results, scope);
          await this.store.setLastSync(scope);
        } else {
          for (const row of rows) {
            this.applyFailure(row, error?.status ?? 0, error?.message ?? 'Fallo de sincronización');
            await this.store.updateOutbox(row);
            if (row.operation_type === 'venta.crear') await this.reconcileSale(row, null, row.status, row.error_message);
            if (row.operation_type.startsWith('cambio.')) await this.reconcileExchange(row, null);
          }
        }
      }
    } finally {
      this.syncing = false;
      await this.refresh();
    }
  }

  private async applyResults(rows: OutboxOperation[], results: Array<Record<string, unknown>>, scope: string): Promise<void> {
    const byId = new Map(results.map(result => [String(result['operation_uuid']), result]));
    for (const row of rows) {
      if (row.tenant_scope !== scope) { row.status = 'RECHAZADA'; row.error_category = 'NO_AUTORIZADA'; row.error_message = 'La organización activa cambió antes del envío.'; }
      else {
        const result = byId.get(row.operation_uuid);
        if (!result) { row.status = 'ERROR_REINTENTABLE'; row.error_message = 'El servidor omitió el resultado de esta operación.'; }
        else {
          row.status = this.status(result['status']);
          row.error_category = result['category'] as string | undefined;
          row.error_message = result['message'] as string | undefined;
          row.result = result['result'] as Record<string, unknown> | undefined;
        }
      }
      await this.store.updateOutbox(row);
      if (row.operation_type.startsWith('reserva.')) {
        const result = byId.get(row.operation_uuid);
        await this.reservations.reconcile(row, {
          operation_uuid: row.operation_uuid,
          status: row.status,
          category: row.error_category,
          message: row.error_message,
          result: result?.['result'] as Record<string, unknown> | undefined
        });
      } else if (row.operation_type === 'venta.crear') {
        const result = byId.get(row.operation_uuid);
        await this.reconcileSale(row, result?.['result'] as Record<string, any> | null ?? null, row.status, row.error_message);
      } else if (row.operation_type.startsWith('cambio.')) {
        await this.reconcileExchange(row, byId.get(row.operation_uuid)?.['result'] as Record<string, any> | null ?? null);
      }
    }
  }

  private status(value: unknown): OutboxStatus {
    return ['SINCRONIZADA', 'RECHAZADA', 'ERROR_REINTENTABLE'].includes(String(value)) ? value as OutboxStatus : 'RECHAZADA';
  }

  private async reconcileSale(operation: OutboxOperation, result: Record<string, any> | null, status: OutboxStatus, message?: string): Promise<void> {
    const userId = Number(operation.payload['id_usuario']);
    if (!Number.isInteger(userId) || userId < 1) return;
    const orders = await this.store.getSalesData<OfflineSaleOrder[]>(operation.tenant_scope, userId, 'orders') ?? [];
    const order = orders.find(item => item.local_operation_uuid === operation.operation_uuid);
    if (!order) return;
    const rejected = Array.isArray(result?.['lineas_rechazadas']) ? result!['lineas_rechazadas'] as any[] : [];
    const accepted = Array.isArray(result?.['lineas_aceptadas']) ? result!['lineas_aceptadas'] as any[] : [];
    for (const line of order.detalles) {
      const rejectedLine = rejected.find(item => item.client_line_id === line['client_line_id']);
      const acceptedLine = accepted.find(item => item.client_line_id === line['client_line_id']);
      if (rejectedLine) {
        line['estado_sync'] = 'RECHAZADA'; line['motivo_rechazo'] = rejectedLine.motivo;
        const variantId = Number(line['id_variante']);
        const stock = await this.store.getSalesData<any[]>(operation.tenant_scope, userId, `stock:${variantId}`) ?? [];
        for (const allocation of line['offline_allocations'] ?? []) {
          const row = stock.find(item => Number(item.id_inventario) === Number(allocation.id_inventario));
          if (row) row.disponible = Number(row.disponible) + Number(allocation.cantidad);
        }
        await this.store.putSalesData(operation.tenant_scope, userId, `stock:${variantId}`, stock);
      } else if (acceptedLine) {
        line['estado_sync'] = 'CONFIRMADA'; line['precio_unitario_confirmado'] = acceptedLine.precio_unitario;
      }
    }
    if (status === 'SINCRONIZADA') {
      const sale = result?.['pedido'];
      if (sale && typeof sale === 'object') {
        Object.assign(order, sale, {
          estado_sync: rejected.length ? 'PARCIAL' : 'CONFIRMADA',
          mensaje_sync: rejected.length ? 'Algunos productos no tenían disponibilidad' : 'Tu compra ha sido confirmada'
        });
      } else {
        order.estado_sync = 'RECHAZADA'; order.mensaje_sync = message ?? 'Ningún producto tenía disponibilidad.';
      }
    } else if (status === 'RECHAZADA') {
      order.estado_sync = 'RECHAZADA'; order.mensaje_sync = message ?? 'La venta fue rechazada por el servidor.';
    } else {
      order.estado_sync = 'ERROR_REINTENTABLE'; order.mensaje_sync = message ?? 'Venta registrada. Esperando confirmación';
    }
    await this.store.putSalesData(operation.tenant_scope, userId, 'orders', orders);
  }

  private async reconcileExchange(operation: OutboxOperation, result: Record<string, any> | null): Promise<void> {
    const rows = await this.cachedExchanges();
    const index = rows.findIndex(row => row.local_operation_uuid === operation.operation_uuid);
    if (index < 0) return;
    rows[index] = { ...rows[index], ...result, sync_status: operation.status,
      sync_message: operation.error_message ?? null,
      state: operation.status === 'SINCRONIZADA' ? result?.['state'] ?? rows[index].state : operation.status };
    await this.cacheExchanges(rows);
  }

  private applyFailure(row: OutboxOperation, status: number, message: string): void {
    row.status = status === 0 || status >= 500 ? 'ERROR_REINTENTABLE' : 'RECHAZADA';
    row.error_category = status === 401 || status === 403 ? 'NO_AUTORIZADA' : status === 409 ? 'UUID_REUTILIZADO' : status >= 500 || status === 0 ? 'TEMPORAL' : 'DATOS_INVALIDOS';
    row.error_message = message;
  }
}

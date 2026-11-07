import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../auth/services/auth.service';
import { TokenService } from '../../core/services/token.service';
import { OutboxSyncService } from '../../core/services/outbox-sync.service';
import { ReservationOfflineStore } from './reservation-offline.store';
import { firstValueFrom, Subscription } from 'rxjs';

interface Availability { id_inventario: number; id_variante: number; producto: string; talla: string; color: string; sucursal: string; disponible: number; }
interface Reservation extends Availability { id_reserva?: number; cantidad: number; estado: string; local_operation_uuid?: string; local_cancel_operation_uuid?: string; sync_status?: string; sync_message?: string; }

@Component({
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `<main class="reservations-page"><h1>Reservas</h1>
    @if (selectedVariantId) { <section class="new-reservation"><h2>Nueva reserva</h2><div class="product-summary">@if (selectedImage) { <img [src]="selectedImage" [alt]="selectedProductName" /> }<div><p>Producto: <strong>{{ selectedProductName || 'la prenda seleccionada' }}</strong></p><p>Talla: <strong>{{ selectedSize }}</strong></p><p>Color: <strong>{{ selectedColor }}</strong></p><p>Precio: <strong>Bs {{ selectedPrice }}</strong></p></div></div><p class="selection-summary">Solo se muestran sucursales con stock disponible para esta variante.</p></section> }
    <p role="status">{{message}}</p>
    @if (offlineMode) { <p role="status">Modo offline: disponibilidad de la última descarga; el servidor confirmará la reserva al sincronizar.</p> }
    @if (isClient) { <button (click)="syncNow()" [disabled]="busy">Sincronizar reservas pendientes</button> }
    @if (isClient) {
      <form (ngSubmit)="reserve()"><label>{{ selectedVariantId ? 'Sucursal disponible' : 'Prenda y sucursal' }}
        <select name="inventory" [(ngModel)]="inventory" required>
          <option [ngValue]="0">Seleccionar</option>
          @for (i of available; track i.id_inventario) { <option [ngValue]="i.id_inventario">{{i.producto}} · {{i.talla}} · {{i.color}} · {{i.sucursal}} (Stock: {{i.disponible}})</option> }
        </select></label>
        @if (selectedVariantId && !available.length) { <p>No hay stock disponible de esta prenda en ninguna sucursal.</p> }
        <label>Cantidad <input name="quantity" type="number" min="1" max="1000" [(ngModel)]="quantity" required></label>
        <button [disabled]="busy || !inventory || quantity < 1 || quantity > 1000">{{ selectedVariantId ? 'Confirmar reserva' : 'Reservar' }}</button>
      </form>
    }
    <button (click)="load()" [disabled]="busy">Actualizar</button>
    @for (r of reservations; track r.local_operation_uuid || r.id_reserva) {
      <article><strong>{{r.id_reserva ? '#' + r.id_reserva : 'Local'}} {{r.producto}}</strong> · {{r.talla}} · {{r.color}} · {{r.sucursal}} · {{r.cantidad}} unidades · {{r.estado}}
        @if (r.estado === 'CANCELADA') { <p>Reserva cancelada. El inventario fue liberado una sola vez.</p> }
        @if (r.sync_status === 'PENDIENTE' || r.sync_status === 'ENVIANDO' || r.sync_status === 'ERROR_REINTENTABLE') { <p>Reserva registrada. Esperando confirmación del servidor.</p> }
        @if (r.sync_message && r.sync_status === 'RECHAZADA') { <p role="alert">{{r.sync_message}}</p> }
        @if (r.estado !== 'CANCELADA' && r.estado !== 'RECHAZADA') {
          @if (!isClient && r.estado === 'PENDIENTE') { <button (click)="update(r, 'CONFIRMADA')" [disabled]="busy">Confirmar</button> }
          @if (!isClient && r.estado === 'CONFIRMADA') { <button (click)="update(r, 'ATENDIDA')" [disabled]="busy">Atender</button> }
          <button (click)="update(r, 'CANCELADA')" [disabled]="busy">Cancelar y liberar stock</button>
        }
      </article>
    } @empty { <p>No hay reservas.</p> }
  </main>`,
  styles: ['.reservations-page{padding:2rem}.new-reservation{max-width:42rem;border:1px solid #d7dfda;border-radius:12px;padding:1rem;margin:1rem 0}.product-summary{display:flex;gap:1rem;align-items:center}.product-summary img{width:5rem;height:5rem;object-fit:cover;border-radius:8px}.product-summary p{margin:.3rem 0}.selection-summary{background:#eef6f0;border-radius:.5rem;color:#245334;padding:.75rem}form{display:grid;gap:.75rem;max-width:38rem}label{display:grid;gap:.25rem}select,input{padding:.5rem}article{border-top:1px solid #ddd;margin-top:1rem;padding-top:1rem}button{margin:.25rem}']
})
export class ReservationsComponent implements OnInit, OnDestroy {
  private api = inject(ApiService);
  private auth = inject(AuthService);
  private route = inject(ActivatedRoute);
  private tokens = inject(TokenService);
  private outbox = inject(OutboxSyncService);
  private offline = inject(ReservationOfflineStore);
  isClient = this.auth.getRoleFromToken(this.tokens.getToken() ?? '') === 'CLIENTE';
  available: Availability[] = [];
  reservations: Reservation[] = [];
  inventory = 0;
  quantity = 1;
  busy = false;
  message = '';
  offlineMode = !navigator.onLine;
  selectedVariantId = 0;
  selectedProductName = '';
  selectedSize = '';
  selectedColor = '';
  selectedPrice = '';
  selectedImage = '';
  private syncSubscription?: Subscription;

  ngOnInit(): void {
    this.syncSubscription = this.outbox.summary$.subscribe(() => { void this.refreshLocalReservations(); });
    const variant = Number(this.route.snapshot.queryParamMap.get('variante_id'));
    this.selectedVariantId = Number.isInteger(variant) && variant > 0 ? variant : 0;
    this.selectedProductName = this.route.snapshot.queryParamMap.get('producto_nombre') ?? '';
    this.selectedSize = this.route.snapshot.queryParamMap.get('talla') ?? '';
    this.selectedColor = this.route.snapshot.queryParamMap.get('color') ?? '';
    this.selectedPrice = this.route.snapshot.queryParamMap.get('precio') ?? '';
    this.selectedImage = this.route.snapshot.queryParamMap.get('imagen') ?? '';
    this.load();
  }

  ngOnDestroy(): void { this.syncSubscription?.unsubscribe(); }

  private async refreshLocalReservations(): Promise<void> {
    if (!this.isClient) return;
    const organizationId = this.tokens.getOrganizationId();
    const userId = this.tokens.getUserId();
    if (!organizationId || !userId) return;
    const scope = `org:${organizationId}`;
    const [reservations, availability] = await Promise.all([
      this.offline.readReservations(scope, userId), this.offline.readAvailability(scope, userId)
    ]);
    if (reservations.length) this.reservations = reservations as Reservation[];
    if (availability.length) this.available = availability as Availability[];
  }

  get selectedStock(): number { return this.available.find(item => item.id_inventario === this.inventory)?.disponible ?? 0; }
  fail = (error: any): void => { this.busy = false; this.message = error.error?.detail || error.error?.message || 'No se pudo completar la operación'; };
  async load(): Promise<void> {
    if (!this.isClient) {
      this.api.get<Reservation[]>('/api/reservations').subscribe({ next: rows => this.reservations = rows, error: this.fail });
      return;
    }
    const organizationId = this.tokens.getOrganizationId();
    const userId = this.tokens.getUserId();
    if (!organizationId || !userId) { this.message = 'Inicia sesión para consultar tus reservas.'; return; }
    const scope = `org:${organizationId}`;
    const availabilityUrl = this.selectedVariantId ? `/api/reservations/availability?id_variante=${this.selectedVariantId}` : '/api/reservations/availability';
    if (!navigator.onLine) {
      this.reservations = await this.offline.readReservations(scope, userId) as Reservation[];
      this.available = await this.offline.readAvailability(scope, userId) as Availability[];
      this.offlineMode = true;
      if (!this.reservations.length && !this.available.length) this.message = 'No hay reservas ni disponibilidad descargadas para consultar sin conexión.';
      return;
    }
    try {
      const [remoteReservations, remoteAvailability] = await Promise.all([
        firstValueFrom(this.api.get<Reservation[]>('/api/reservations')),
        firstValueFrom(this.api.get<Availability[]>(availabilityUrl))
      ]);
      const cachedReservations = await this.offline.readReservations(scope, userId);
      const localRows = cachedReservations.filter(row => row.local_operation_uuid || row.local_cancel_operation_uuid || row.estado === 'RECHAZADA');
      const pending = localRows.filter(row => ['PENDIENTE', 'ENVIANDO', 'ERROR_REINTENTABLE'].includes(String(row.sync_status)));
      this.reservations = [...remoteReservations, ...(localRows as Reservation[]).filter(local =>
        !remoteReservations.some(remote => Number(remote.id_reserva) === Number(local.id_reserva) && local.id_reserva))];
      // Keep the provisional stock view while this user's own operations are unresolved.
      this.available = pending.length
        ? await this.offline.readAvailability(scope, userId) as Availability[]
        : remoteAvailability;
      await Promise.all([
        this.offline.saveReservations(scope, userId, this.reservations),
        this.offline.saveAvailability(scope, userId, this.available)
      ]);
      this.offlineMode = false;
    } catch (error) {
      this.reservations = await this.offline.readReservations(scope, userId) as Reservation[];
      this.available = await this.offline.readAvailability(scope, userId) as Availability[];
      this.offlineMode = true;
      if (!this.reservations.length && !this.available.length) this.fail(error);
      else this.message = 'Catálogo y disponibilidad descargados anteriormente; el servidor confirmará el resultado.';
    }
    this.selectedProductName ||= this.available[0]?.producto ?? '';
    this.selectedSize ||= this.available[0]?.talla ?? '';
    this.selectedColor ||= this.available[0]?.color ?? '';
    if (!this.available.some(item => item.id_inventario === this.inventory)) this.inventory = 0;
  }

  async reserve(): Promise<void> {
    const organizationId = this.tokens.getOrganizationId();
    const userId = this.tokens.getUserId();
    if (this.busy || !organizationId || !userId || !this.inventory || this.quantity < 1 || this.quantity > 1000) return;
    const selected = this.available.find(item => item.id_inventario === this.inventory);
    if (!selected) { this.message = 'Selecciona una sucursal descargada previamente.'; return; }
    this.busy = true;
    try {
      const operation = await this.outbox.enqueue('reserva.crear', { id_inventario: this.inventory, cantidad: this.quantity, id_usuario: userId });
      this.reservations.unshift({ ...selected, id_reserva: 0, cantidad: this.quantity, estado: 'PENDIENTE', local_operation_uuid: operation.operation_uuid, sync_status: 'PENDIENTE' });
      selected.disponible = Math.max(0, selected.disponible - this.quantity);
      await Promise.all([
        this.offline.saveReservations(`org:${organizationId}`, userId, this.reservations),
        this.offline.saveAvailability(`org:${organizationId}`, userId, this.available)
      ]);
      await this.outbox.syncPending();
      this.reservations = await this.offline.readReservations(`org:${organizationId}`, userId) as Reservation[];
      const saved = this.reservations.find(row => row.local_operation_uuid === operation.operation_uuid);
      this.message = saved?.sync_status === 'SINCRONIZADA'
        ? 'Tu reserva ha sido confirmada'
        : saved?.sync_status === 'RECHAZADA' ? saved.sync_message ?? 'No se pudo confirmar la reserva.'
        : 'Reserva registrada. Esperando confirmación del servidor';
    } catch (error: any) { this.fail(error); }
    finally { this.busy = false; }
  }

  async update(r: Reservation, estado: string): Promise<void> {
    if (this.isClient && estado === 'CANCELADA') {
      const userId = this.tokens.getUserId();
      const organizationId = this.tokens.getOrganizationId();
      if (!userId || !organizationId) return;
      this.busy = true;
      try {
        if (r.local_operation_uuid && !r.id_reserva) {
          const removed = await this.outbox.removeUnsent(r.local_operation_uuid);
          if (!removed) { this.message = 'Espera a que termine el envío antes de cancelar.'; return; }
          this.reservations = this.reservations.filter(item => item.local_operation_uuid !== r.local_operation_uuid);
          const inventory = this.available.find(item => item.id_inventario === r.id_inventario);
          if (inventory) inventory.disponible += r.cantidad;
          this.message = 'Reserva local cancelada antes del envío.';
        } else {
          const operation = await this.outbox.enqueue('reserva.cancelar', {
            id_reserva: r.id_reserva, id_usuario: userId, id_inventario: r.id_inventario,
            cantidad: r.cantidad, estado_anterior: r.estado
          });
          r.estado = 'CANCELACION_PENDIENTE'; r.sync_status = 'PENDIENTE'; r.local_cancel_operation_uuid = operation.operation_uuid;
          const inventory = this.available.find(item => item.id_inventario === r.id_inventario);
          if (inventory) inventory.disponible += r.cantidad;
          await this.outbox.syncPending();
          this.reservations = await this.offline.readReservations(`org:${organizationId}`, userId) as Reservation[];
          const updated = this.reservations.find(item => item.id_reserva === r.id_reserva);
          this.message = updated?.estado === 'CANCELADA' ? 'Tu reserva ha sido cancelada'
            : updated?.sync_status === 'RECHAZADA' ? updated.sync_message ?? 'No se pudo cancelar la reserva.'
            : 'Cancelación registrada. Esperando confirmación del servidor';
        }
        await Promise.all([
          this.offline.saveReservations(`org:${organizationId}`, userId, this.reservations),
          this.offline.saveAvailability(`org:${organizationId}`, userId, this.available)
        ]);
      } catch (error: any) { this.fail(error); }
      finally { this.busy = false; }
      return;
    }
    this.busy = true;
    this.api.put<Reservation>(`/api/reservations/${r.id_reserva}`, { estado }).subscribe({ next: updated => {
      this.busy = false;
      r.estado = updated.estado;
      this.message = updated.estado === 'CANCELADA' ? 'Reserva cancelada; el inventario está liberado.' : 'Reserva actualizada';
      this.load();
    }, error: this.fail });
  }

  async syncNow(): Promise<void> {
    this.busy = true;
    await this.outbox.syncPending();
    await this.load();
    this.busy = false;
  }
}

import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../auth/services/auth.service';
import { TokenService } from '../../core/services/token.service';

interface Availability { id_inventario: number; producto: string; talla: string; color: string; sucursal: string; disponible: number; }
interface Reservation extends Availability { id_reserva: number; cantidad: number; estado: string; }

@Component({
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `<main style="padding:2rem"><h1>Reservas</h1>
    <p role="status">{{message}}</p>
    @if (isClient) {
      <form (ngSubmit)="reserve()"><label>Prenda y sucursal
        <select name="inventory" [(ngModel)]="inventory" required>
          <option [ngValue]="0">Seleccionar</option>
          @for (i of available; track i.id_inventario) { <option [ngValue]="i.id_inventario">{{i.producto}} · {{i.talla}} · {{i.color}} · {{i.sucursal}} ({{i.disponible}})</option> }
        </select></label>
        <label>Cantidad <input name="quantity" type="number" min="1" max="1000" [(ngModel)]="quantity" required></label>
        <button [disabled]="busy || !inventory || quantity < 1">Reservar</button>
      </form>
    }
    <button (click)="load()" [disabled]="busy">Actualizar</button>
    @for (r of reservations; track r.id_reserva) {
      <article style="padding:1rem;border-bottom:1px solid #ccc">
        <strong>#{{r.id_reserva}} {{r.producto}}</strong> · {{r.talla}} · {{r.color}} · {{r.sucursal}} · {{r.cantidad}} unidades · {{r.estado}}
        @if (r.estado !== 'CANCELADA') {
          @if (!isClient && r.estado === 'PENDIENTE') { <button (click)="update(r, 'CONFIRMADA')" [disabled]="busy">Confirmar</button> }
          @if (!isClient && r.estado === 'CONFIRMADA') { <button (click)="update(r, 'ATENDIDA')" [disabled]="busy">Atender</button> }
          <button (click)="update(r, 'CANCELADA')" [disabled]="busy">Cancelar y liberar stock</button>
        }
      </article>
    } @empty { <p>No hay reservas.</p> }
  </main>`
})
export class ReservationsComponent implements OnInit {
  private api = inject(ApiService);
  private auth = inject(AuthService);
  isClient = this.auth.getRoleFromToken(inject(TokenService).getToken() ?? '') === 'CLIENTE';
  available: Availability[] = [];
  reservations: Reservation[] = [];
  inventory = 0;
  quantity = 1;
  busy = false;
  message = '';
  ngOnInit(): void { this.load(); }
  fail = (error: any): void => { this.busy = false; this.message = error.error?.detail || error.error?.message || 'No se pudo completar la operación'; };
  load(): void {
    this.api.get<Reservation[]>('/api/reservations').subscribe({ next: rows => this.reservations = rows, error: this.fail });
    if (this.isClient) this.api.get<Availability[]>('/api/reservations/availability').subscribe({ next: rows => this.available = rows, error: this.fail });
  }
  reserve(): void {
    if (this.busy || !this.inventory || this.quantity < 1) return;
    this.busy = true;
    this.api.post('/api/reservations', { id_inventario: this.inventory, cantidad: this.quantity }).subscribe({ next: () => { this.busy = false; this.message = 'Reserva creada'; this.load(); }, error: this.fail });
  }
  update(r: Reservation, estado: string): void {
    this.busy = true;
    this.api.put(`/api/reservations/${r.id_reserva}`, { estado }).subscribe({ next: () => { this.busy = false; this.message = 'Reserva actualizada'; this.load(); }, error: this.fail });
  }
}

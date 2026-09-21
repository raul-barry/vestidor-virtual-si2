import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../auth/services/auth.service';
import { TokenService } from '../../core/services/token.service';

interface Availability { id_inventario: number; id_variante: number; producto: string; talla: string; color: string; sucursal: string; disponible: number; }
interface Reservation extends Availability { id_reserva: number; cantidad: number; estado: string; }

@Component({
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `<main class="reservations-page"><h1>Reservas</h1>
    @if (selectedVariantId) { <section class="new-reservation"><h2>Nueva reserva</h2><div class="product-summary">@if (selectedImage) { <img [src]="selectedImage" [alt]="selectedProductName" /> }<div><p>Producto: <strong>{{ selectedProductName || 'la prenda seleccionada' }}</strong></p><p>Talla: <strong>{{ selectedSize }}</strong></p><p>Color: <strong>{{ selectedColor }}</strong></p><p>Precio: <strong>Bs {{ selectedPrice }}</strong></p></div></div><p class="selection-summary">Solo se muestran sucursales con stock disponible para esta variante.</p></section> }
    <p role="status">{{message}}</p>
    @if (isClient) {
      <form (ngSubmit)="reserve()"><label>{{ selectedVariantId ? 'Sucursal disponible' : 'Prenda y sucursal' }}
        <select name="inventory" [(ngModel)]="inventory" required>
          <option [ngValue]="0">Seleccionar</option>
          @for (i of available; track i.id_inventario) { <option [ngValue]="i.id_inventario">{{i.producto}} · {{i.talla}} · {{i.color}} · {{i.sucursal}} (Stock: {{i.disponible}})</option> }
        </select></label>
        @if (selectedVariantId && !available.length) { <p>No hay stock disponible de esta prenda en ninguna sucursal.</p> }
        <label>Cantidad <input name="quantity" type="number" min="1" [max]="selectedStock || 1000" [(ngModel)]="quantity" required></label>
        <button [disabled]="busy || !inventory || quantity < 1 || (selectedStock > 0 && quantity > selectedStock)">{{ selectedVariantId ? 'Confirmar reserva' : 'Reservar' }}</button>
      </form>
    }
    <button (click)="load()" [disabled]="busy">Actualizar</button>
    @for (r of reservations; track r.id_reserva) {
      <article><strong>#{{r.id_reserva}} {{r.producto}}</strong> · {{r.talla}} · {{r.color}} · {{r.sucursal}} · {{r.cantidad}} unidades · {{r.estado}}
        @if (r.estado !== 'CANCELADA') {
          @if (!isClient && r.estado === 'PENDIENTE') { <button (click)="update(r, 'CONFIRMADA')" [disabled]="busy">Confirmar</button> }
          @if (!isClient && r.estado === 'CONFIRMADA') { <button (click)="update(r, 'ATENDIDA')" [disabled]="busy">Atender</button> }
          <button (click)="update(r, 'CANCELADA')" [disabled]="busy">Cancelar y liberar stock</button>
        }
      </article>
    } @empty { <p>No hay reservas.</p> }
  </main>`,
  styles: ['.reservations-page{padding:2rem}.new-reservation{max-width:42rem;border:1px solid #d7dfda;border-radius:12px;padding:1rem;margin:1rem 0}.product-summary{display:flex;gap:1rem;align-items:center}.product-summary img{width:5rem;height:5rem;object-fit:cover;border-radius:8px}.product-summary p{margin:.3rem 0}.selection-summary{background:#eef6f0;border-radius:.5rem;color:#245334;padding:.75rem}form{display:grid;gap:.75rem;max-width:38rem}label{display:grid;gap:.25rem}select,input{padding:.5rem}article{border-top:1px solid #ddd;margin-top:1rem;padding-top:1rem}button{margin:.25rem}']
})
export class ReservationsComponent implements OnInit {
  private api = inject(ApiService);
  private auth = inject(AuthService);
  private route = inject(ActivatedRoute);
  isClient = this.auth.getRoleFromToken(inject(TokenService).getToken() ?? '') === 'CLIENTE';
  available: Availability[] = [];
  reservations: Reservation[] = [];
  inventory = 0;
  quantity = 1;
  busy = false;
  message = '';
  selectedVariantId = 0;
  selectedProductName = '';
  selectedSize = '';
  selectedColor = '';
  selectedPrice = '';
  selectedImage = '';

  ngOnInit(): void {
    const variant = Number(this.route.snapshot.queryParamMap.get('variante_id'));
    this.selectedVariantId = Number.isInteger(variant) && variant > 0 ? variant : 0;
    this.selectedProductName = this.route.snapshot.queryParamMap.get('producto_nombre') ?? '';
    this.selectedSize = this.route.snapshot.queryParamMap.get('talla') ?? '';
    this.selectedColor = this.route.snapshot.queryParamMap.get('color') ?? '';
    this.selectedPrice = this.route.snapshot.queryParamMap.get('precio') ?? '';
    this.selectedImage = this.route.snapshot.queryParamMap.get('imagen') ?? '';
    this.load();
  }

  get selectedStock(): number { return this.available.find(item => item.id_inventario === this.inventory)?.disponible ?? 0; }
  fail = (error: any): void => { this.busy = false; this.message = error.error?.detail || error.error?.message || 'No se pudo completar la operación'; };
  load(): void {
    this.api.get<Reservation[]>('/api/reservations').subscribe({ next: rows => this.reservations = rows, error: this.fail });
    if (this.isClient) {
      const availabilityUrl = this.selectedVariantId ? `/api/reservations/availability?id_variante=${this.selectedVariantId}` : '/api/reservations/availability';
      this.api.get<Availability[]>(availabilityUrl).subscribe({
        next: rows => { this.available = rows; this.selectedProductName = this.selectedProductName || rows[0]?.producto || ''; this.selectedSize = this.selectedSize || rows[0]?.talla || ''; this.selectedColor = this.selectedColor || rows[0]?.color || ''; if (!rows.some(item => item.id_inventario === this.inventory)) this.inventory = 0; },
        error: this.fail
      });
    }
  }
  reserve(): void {
    if (this.busy || !this.inventory || this.quantity < 1 || (this.selectedStock > 0 && this.quantity > this.selectedStock)) return;
    this.busy = true;
    this.api.post('/api/reservations', { id_inventario: this.inventory, cantidad: this.quantity }).subscribe({ next: () => { this.busy = false; this.message = 'Reserva creada'; this.load(); }, error: this.fail });
  }
  update(r: Reservation, estado: string): void {
    this.busy = true;
    this.api.put(`/api/reservations/${r.id_reserva}`, { estado }).subscribe({ next: () => { this.busy = false; this.message = 'Reserva actualizada'; this.load(); }, error: this.fail });
  }
}

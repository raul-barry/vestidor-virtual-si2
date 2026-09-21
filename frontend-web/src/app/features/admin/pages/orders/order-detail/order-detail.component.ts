import { Component, OnInit, inject } from '@angular/core';
import { CurrencyPipe } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { OrderDetailAdmin } from '../../../models/order-admin.model';
import { OrderAdminService } from '../../../services/order-admin.service';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { ErrorMessageComponent } from '../../../shared/components/error-message/error-message.component';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { BackLinkComponent } from '../../../../../shared/components/back-link.component';

@Component({
  selector: 'app-order-detail-admin', standalone: true,
  imports: [CurrencyPipe, MatCardModule, MatSnackBarModule, LoadingSpinnerComponent, EmptyStateComponent, ErrorMessageComponent, BackLinkComponent],
  template: `<section class="page"><app-back-link [to]="['/admin/orders']" label="Volver a ventas" />
    @if (loading) { <app-loading-spinner /> }
    @else if (error) { <app-error-message message="Pedido inexistente o no disponible." /> }
    @else if (order) {
      <h1>Pedido #{{ order.id_pedido }}</h1>
      <mat-card><mat-card-content><p>Cliente: {{ order.cliente }}</p><p>Fecha: {{ order.fecha }}</p><p>Estado: {{ order.estado }}</p><strong>Total: {{ order.total | currency:'BOB' }}</strong></mat-card-content></mat-card>
      <mat-card><mat-card-content>@for (detail of order.detalles; track $index) { <p>{{ detail.producto }} · {{ detail.talla }} · {{ detail.color }} — {{ detail.cantidad }} x {{ detail.precio_unitario }}</p> }</mat-card-content></mat-card>
      @if (order.pago) { <mat-card><mat-card-content>Pago {{ order.pago.metodo_pago }} — {{ order.pago.estado }} — {{ order.pago.monto }}</mat-card-content></mat-card> }
    }
  </section>`,
  styles: ['.page{padding:2rem;display:grid;gap:1rem}']
})
export class OrderDetailComponent implements OnInit {
  private route = inject(ActivatedRoute); private service = inject(OrderAdminService); private snack = inject(MatSnackBar);
  order: OrderDetailAdmin | null = null; loading = true; error = false;
  ngOnInit(): void { const id = Number(this.route.snapshot.paramMap.get('id')); this.service.getOrderDetail(id).subscribe({ next: (order) => { this.order = order; this.loading = false; }, error: () => { this.error = true; this.loading = false; this.snack.open('No fue posible cargar el pedido', 'Cerrar', { duration: 5000 }); } }); }
}

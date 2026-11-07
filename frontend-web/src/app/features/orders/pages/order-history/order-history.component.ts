import { Component, OnInit, inject } from '@angular/core';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Order } from '../../../../shared/models/order.model';
import { OrderCardComponent } from '../../components/order-card/order-card.component';
import { OrderService } from '../../services/order.service';
import { OfflineSaleOrder, OutboxSyncService } from '../../../../core/services/outbox-sync.service';

@Component({
  selector: 'app-order-history',
  standalone: true,
  imports: [MatCardModule, MatButtonModule, MatProgressSpinnerModule, MatSnackBarModule, OrderCardComponent],
  templateUrl: './order-history.component.html',
  styleUrl: './order-history.component.scss'
})
export class OrderHistoryComponent implements OnInit {
  private readonly orderService = inject(OrderService);
  private readonly router = inject(Router);
  private readonly snackBar = inject(MatSnackBar);
  private readonly outbox = inject(OutboxSyncService);

  orders: Order[] = [];
  offlineOrders: OfflineSaleOrder[] = [];
  isLoading = true;

  ngOnInit(): void {
    void this.outbox.localOrders().then(orders => this.offlineOrders = orders);
    this.orderService.getOrders().subscribe({
      next: (orders) => {
        void this.outbox.localOrders().then(local => {
          this.offlineOrders = local;
          this.orders = orders.filter(order => !local.some(item => item.id_pedido === order.id_pedido));
        });
        this.isLoading = false;
      },
      error: (error: { error?: { message?: string } }) => {
        void this.outbox.localOrders().then(local => {
          this.offlineOrders = local;
          this.isLoading = false;
          if (!local.length) this.snackBar.open(error.error?.message ?? 'No fue posible cargar los pedidos', 'Cerrar', { duration: 5000 });
        });
      }
    });
  }

  async syncPending(): Promise<void> {
    await this.outbox.syncPending();
    this.offlineOrders = await this.outbox.localOrders();
  }

  viewOrderDetail(id_pedido: number): void {
    void this.router.navigate(['/orders/detail', id_pedido]);
  }
}

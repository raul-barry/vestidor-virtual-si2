import { Component, OnInit, inject } from '@angular/core';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Order } from '../../../../shared/models/order.model';
import { OrderCardComponent } from '../../components/order-card/order-card.component';
import { OrderService } from '../../services/order.service';

@Component({
  selector: 'app-order-history',
  standalone: true,
  imports: [MatCardModule, MatProgressSpinnerModule, MatSnackBarModule, OrderCardComponent],
  templateUrl: './order-history.component.html',
  styleUrl: './order-history.component.scss'
})
export class OrderHistoryComponent implements OnInit {
  private readonly orderService = inject(OrderService);
  private readonly router = inject(Router);
  private readonly snackBar = inject(MatSnackBar);

  orders: Order[] = [];
  isLoading = true;

  ngOnInit(): void {
    this.orderService.getOrders().subscribe({
      next: (orders) => {
        this.orders = orders;
        this.isLoading = false;
      },
      error: (error: { error?: { message?: string } }) => {
        this.isLoading = false;
        this.snackBar.open(error.error?.message ?? 'No fue posible cargar los pedidos', 'Cerrar', {
          duration: 5000
        });
      }
    });
  }

  viewOrderDetail(id_pedido: number): void {
    void this.router.navigate(['/orders/detail', id_pedido]);
  }
}

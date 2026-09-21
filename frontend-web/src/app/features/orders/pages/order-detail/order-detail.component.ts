import { Component, OnInit, inject } from '@angular/core';
import { CurrencyPipe, DatePipe } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Order } from '../../../../shared/models/order.model';
import { OrderService } from '../../services/order.service';
import { BackLinkComponent } from '../../../../shared/components/back-link.component';
import { OrderStatusTrackerComponent } from '../../components/order-status-tracker.component';

@Component({
  selector: 'app-order-detail',
  standalone: true,
  imports: [CurrencyPipe, DatePipe, MatButtonModule, MatCardModule, MatProgressSpinnerModule, MatSnackBarModule, BackLinkComponent, OrderStatusTrackerComponent],
  templateUrl: './order-detail.component.html',
  styleUrl: './order-detail.component.scss'
})
export class OrderDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly orderService = inject(OrderService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly router = inject(Router);

  order: Order | null = null;
  isLoading = true;
  isNotFound = false;

  ngOnInit(): void {
    const orderId = Number(this.route.snapshot.paramMap.get('id'));
    if (!Number.isInteger(orderId) || orderId <= 0) {
      this.handleError({ status: 404 });
      return;
    }

    this.orderService.getOrderDetail(orderId).subscribe({
      next: (order) => {
        this.order = order;
        this.isLoading = false;
      },
      error: (error: { status?: number; error?: { message?: string } }) => this.handleError(error)
    });
  }

  payOrder(): void {
    if (this.order) {
      void this.router.navigate(['/payments', this.order.id_pedido]);
    }
  }

  private handleError(error: { status?: number; error?: { message?: string } }): void {
    this.isLoading = false;
    this.isNotFound = error.status === 404;
    this.snackBar.open(error.error?.message ?? 'No fue posible cargar el pedido', 'Cerrar', {
      duration: 5000
    });
  }
}

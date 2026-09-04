import { Component, OnInit, inject } from '@angular/core';
import { CurrencyPipe } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Cart } from '../../../../shared/models/cart.model';
import { Order } from '../../../../shared/models/order.model';
import { CartService } from '../../../cart/services/cart.service';
import { OrderService } from '../../services/order.service';

@Component({
  selector: 'app-checkout',
  standalone: true,
  imports: [
    CurrencyPipe,
    MatButtonModule,
    MatCardModule,
    MatProgressSpinnerModule,
    MatSnackBarModule
  ],
  templateUrl: './checkout.component.html',
  styleUrl: './checkout.component.scss'
})
export class CheckoutComponent implements OnInit {
  private readonly cartService = inject(CartService);
  private readonly orderService = inject(OrderService);
  private readonly snackBar = inject(MatSnackBar);

  cart: Cart | null = null;
  createdOrder: Order | null = null;
  isLoading = true;
  isSubmitting = false;

  ngOnInit(): void {
    this.cartService.getCart().subscribe({
      next: (cart) => {
        this.cart = cart;
        this.isLoading = false;
      },
      error: (error: { error?: { message?: string } }) => this.handleLoadError(error)
    });
  }

  createOrder(): void {
    if (!this.cart || this.cart.items.length === 0) {
      this.snackBar.open('Tu carrito está vacío', 'Cerrar', { duration: 4000 });
      return;
    }

    this.isSubmitting = true;
    this.orderService.createOrder().subscribe({
      next: (order) => {
        this.createdOrder = order;
        this.isSubmitting = false;
        this.snackBar.open('Pedido creado correctamente', 'Cerrar', { duration: 3000 });
      },
      error: (error: { error?: { message?: string } }) => {
        this.isSubmitting = false;
        this.snackBar.open(error.error?.message ?? 'No fue posible crear el pedido', 'Cerrar', {
          duration: 5000
        });
      }
    });
  }

  private handleLoadError(error: { error?: { message?: string } }): void {
    this.isLoading = false;
    this.snackBar.open(error.error?.message ?? 'No fue posible cargar el carrito', 'Cerrar', {
      duration: 5000
    });
  }
}

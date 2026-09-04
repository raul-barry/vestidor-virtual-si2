import { Component, OnInit, inject } from '@angular/core';
import { CurrencyPipe } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { Router } from '@angular/router';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Cart, CartItem } from '../../../../shared/models/cart.model';
import { CartItemComponent } from '../../components/cart-item/cart-item.component';
import { CartService } from '../../services/cart.service';

@Component({
  selector: 'app-cart-view',
  standalone: true,
  imports: [
    CurrencyPipe,
    MatCardModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    CartItemComponent
  ],
  templateUrl: './cart-view.component.html',
  styleUrl: './cart-view.component.scss'
})
export class CartViewComponent implements OnInit {
  private readonly cartService = inject(CartService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly router = inject(Router);

  cart: Cart | null = null;
  isLoading = true;

  ngOnInit(): void {
    this.loadCart();
  }

  updateQuantity(item: CartItem, cantidad: number): void {
    this.cartService.updateQuantity(item.id_detalle, cantidad).subscribe({
      next: (cart) => (this.cart = cart),
      error: (error: { error?: { message?: string } }) => this.showError(error)
    });
  }

  removeItem(item: CartItem): void {
    this.cartService.removeItem(item.id_detalle).subscribe({
      next: (cart) => (this.cart = cart),
      error: (error: { error?: { message?: string } }) => this.showError(error)
    });
  }

  checkout(): void {
    void this.router.navigate(['/checkout']);
  }

  private loadCart(): void {
    this.cartService.getCart().subscribe({
      next: (cart) => {
        this.cart = cart;
        this.isLoading = false;
      },
      error: (error: { error?: { message?: string } }) => {
        this.isLoading = false;
        this.showError(error);
      }
    });
  }

  private showError(error: { error?: { message?: string } }): void {
    this.snackBar.open(error.error?.message ?? 'No fue posible actualizar el carrito', 'Cerrar', {
      duration: 5000
    });
  }
}

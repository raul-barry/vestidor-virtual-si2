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
import { OutboxSyncService } from '../../../../core/services/outbox-sync.service';

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
  private readonly outbox = inject(OutboxSyncService);

  cart: Cart | null = null;
  isLoading = true;
  offline = false;

  ngOnInit(): void {
    this.loadCart();
  }

  updateQuantity(item: CartItem, cantidad: number): void {
    if (this.offline) {
      void this.outbox.updateOfflineCartItem(item.id_detalle, cantidad).then(cart => this.cart = cart);
      return;
    }
    this.cartService.updateQuantity(item.id_detalle, cantidad).subscribe({
      next: (cart) => { this.cart = cart; void this.outbox.saveLocalCart(cart); },
      error: (error: { error?: { message?: string } }) => this.showError(error)
    });
  }

  removeItem(item: CartItem): void {
    if (this.offline) {
      void this.outbox.updateOfflineCartItem(item.id_detalle, null).then(cart => this.cart = cart);
      return;
    }
    this.cartService.removeItem(item.id_detalle).subscribe({
      next: (cart) => { this.cart = cart; void this.outbox.saveLocalCart(cart); },
      error: (error: { error?: { message?: string } }) => this.showError(error)
    });
  }

  checkout(): void {
    void this.router.navigate(['/checkout']);
  }

  private loadCart(): void {
    this.cartService.getCart().subscribe({
      next: (serverCart) => {
        void this.outbox.localCart().then(localCart => {
          if (this.outbox.isOfflineModifiedCart(localCart)) {
            this.cart = localCart;
            this.offline = true;
          } else {
            this.cart = serverCart;
            this.offline = false;
            void this.outbox.saveLocalCart(serverCart);
          }
          this.isLoading = false;
        }).catch(() => {
          this.cart = serverCart;
          this.offline = false;
          this.isLoading = false;
        });
      },
      error: (error: { error?: { message?: string } }) => {
        void this.outbox.localCart().then(cart => {
          this.cart = cart;
          this.offline = !!cart;
          this.isLoading = false;
          if (!cart) this.showError(error);
        });
      }
    });
  }

  private showError(error: { error?: { message?: string } }): void {
    this.snackBar.open(error.error?.message ?? 'No fue posible actualizar el carrito', 'Cerrar', {
      duration: 5000
    });
  }
}

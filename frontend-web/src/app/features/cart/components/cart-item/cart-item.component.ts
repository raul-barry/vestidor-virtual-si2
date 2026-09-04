import { CurrencyPipe } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { CartItem } from '../../../../shared/models/cart.model';

@Component({
  selector: 'app-cart-item',
  standalone: true,
  imports: [CurrencyPipe, MatButtonModule, MatCardModule],
  templateUrl: './cart-item.component.html',
  styleUrl: './cart-item.component.scss'
})
export class CartItemComponent {
  @Input({ required: true }) item!: CartItem;
  @Output() readonly quantityChange = new EventEmitter<number>();
  @Output() readonly itemRemoved = new EventEmitter<void>();

  increase(): void {
    this.quantityChange.emit(this.item.cantidad + 1);
  }

  decrease(): void {
    if (this.item.cantidad > 1) {
      this.quantityChange.emit(this.item.cantidad - 1);
    }
  }
}

import { CurrencyPipe } from '@angular/common';
import { Component, Input, inject } from '@angular/core';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { Producto } from '../../../../shared/models/producto.model';

@Component({
  selector: 'app-product-card',
  standalone: true,
  imports: [CurrencyPipe, MatCardModule],
  templateUrl: './product-card.component.html',
  styleUrl: './product-card.component.scss'
})
export class ProductCardComponent {
  private readonly router = inject(Router);

  @Input({ required: true }) producto!: Producto;

  openProduct(): void {
    void this.router.navigate(['/catalog/product', this.producto.id_producto]);
  }
}

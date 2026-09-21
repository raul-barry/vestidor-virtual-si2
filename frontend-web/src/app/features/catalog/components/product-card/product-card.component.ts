import { CurrencyPipe } from '@angular/common';
import { Component, Input, inject } from '@angular/core';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { Producto } from '../../../../shared/models/producto.model';
import { API_URL } from '../../../../core/config/api.config';

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

  get imageClass(): string {
    const name = this.producto.nombre.toLowerCase();
    return name.includes('pantal') ? 'product-image product-image-pants' : name.includes('chaqueta') ? 'product-image product-image-jacket' : 'product-image product-image-shirt';
  }

  get imageUrl(): string {
    const image = this.producto.imagen_url;
    return image ? (image.startsWith('http') ? image : `${API_URL}${image}`) : 'assets/catalog/editorial-menswear.png';
  }

  useFallbackImage(event: Event): void {
    const image = event.target as HTMLImageElement;
    image.onerror = null;
    image.src = 'assets/catalog/editorial-menswear.png';
  }

  openProduct(): void {
    void this.router.navigate(['/catalog/product', this.producto.id_producto]);
  }
}

import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { ProductoVariante, ProductVariantsResponse } from '../../../../shared/models/producto.model';

@Component({
  selector: 'app-variant-selector',
  standalone: true,
  imports: [MatButtonModule, MatChipsModule],
  templateUrl: './variant-selector.component.html',
  styleUrl: './variant-selector.component.scss'
})
export class VariantSelectorComponent {
  @Input({ required: true }) product!: ProductVariantsResponse;
  @Output() readonly selectedVariantChange = new EventEmitter<ProductoVariante | null>();

  selectedSize: string | null = null;
  selectedColor: string | null = null;

  clearSelection(): void {
    this.selectedSize = null;
    this.selectedColor = null;
    this.selectedVariantChange.emit(null);
  }

  selectSize(talla: string): void {
    this.selectedSize = talla;
    this.emitSelectedVariant();
  }

  selectColor(color: string): void {
    this.selectedColor = color;
    this.emitSelectedVariant();
  }

  private emitSelectedVariant(): void {
    const selectedVariant = this.product.variantes.find(
      (variant) => variant.talla === this.selectedSize && variant.color === this.selectedColor
    );
    this.selectedVariantChange.emit(selectedVariant ?? null);
  }
}

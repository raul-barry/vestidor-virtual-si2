import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { forkJoin } from 'rxjs';
import {
  ProductAvailabilityResponse,
  ProductoVariante,
  ProductVariantsResponse
} from '../../../../shared/models/producto.model';
import { AvailabilityListComponent } from '../../components/availability-list/availability-list.component';
import { VariantSelectorComponent } from '../../components/variant-selector/variant-selector.component';
import { CatalogService } from '../../services/catalog.service';
import { CartService } from '../../../cart/services/cart.service';

@Component({
  selector: 'app-product-detail',
  standalone: true,
  imports: [
    MatCardModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    VariantSelectorComponent,
    AvailabilityListComponent
  ],
  templateUrl: './product-detail.component.html',
  styleUrl: './product-detail.component.scss'
})
export class ProductDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly catalogService = inject(CatalogService);
  private readonly cartService = inject(CartService);
  private readonly snackBar = inject(MatSnackBar);

  variants: ProductVariantsResponse | null = null;
  availability: ProductAvailabilityResponse | null = null;
  isLoading = true;
  selectedVariant: ProductoVariante | null = null;
  isAddingToCart = false;

  ngOnInit(): void {
    const productId = Number(this.route.snapshot.paramMap.get('id'));
    if (!Number.isInteger(productId) || productId <= 0) {
      this.handleError();
      return;
    }

    forkJoin({
      variants: this.catalogService.getProductVariants(productId),
      availability: this.catalogService.getProductAvailability(productId)
    }).subscribe({
      next: (response) => {
        this.variants = response.variants;
        this.availability = response.availability;
        this.isLoading = false;
      },
      error: () => this.handleError()
    });
  }

  addToCart(): void {
    if (this.selectedVariant === null) {
      this.snackBar.open('Selecciona una talla y un color disponibles', 'Cerrar', { duration: 4000 });
      return;
    }

    this.isAddingToCart = true;
    this.cartService.addItem(this.selectedVariant.id_variante, 1).subscribe({
      next: () => {
        this.isAddingToCart = false;
        this.snackBar.open('Producto agregado al carrito', 'Cerrar', { duration: 3000 });
      },
      error: (error: { error?: { message?: string } }) => {
        this.isAddingToCart = false;
        this.snackBar.open(error.error?.message ?? 'No fue posible agregar el producto', 'Cerrar', {
          duration: 5000
        });
      }
    });
  }

  private handleError(): void {
    this.isLoading = false;
    this.snackBar.open('No fue posible cargar el detalle del producto', 'Cerrar', { duration: 5000 });
  }
}

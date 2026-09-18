import { RecommendationsSectionComponent } from '../../../experience/recommendations-section.component';
import { Component, OnInit, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Producto } from '../../../../shared/models/producto.model';
import { AuthService } from '../../../auth/services/auth.service';
import { ProductCardComponent } from '../../components/product-card/product-card.component';
import { ProductFilterComponent } from '../../components/product-filter/product-filter.component';
import { CatalogService, ProductSearchFilters } from '../../services/catalog.service';

@Component({
  selector: 'app-catalog-list',
  standalone: true,
  imports: [
    RouterLink,
    RecommendationsSectionComponent,
    MatButtonModule,
    MatCardModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    ProductCardComponent,
    ProductFilterComponent
  ],
  templateUrl: './catalog-list.component.html',
  styleUrl: './catalog-list.component.scss'
})
export class CatalogListComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly catalogService = inject(CatalogService);
  private readonly router = inject(Router);
  private readonly snackBar = inject(MatSnackBar);

  products: Producto[] = [];
  categorias: string[] = [];
  tallas: string[] = [];
  colores: string[] = [];
  isLoading = true;

  ngOnInit(): void {
    this.loadProducts();
  }

  onFiltersChange(filters: ProductSearchFilters): void {
    this.isLoading = true;
    if (Object.keys(filters).length === 0) {
      this.loadProducts();
      return;
    }

    this.catalogService.searchProducts(filters).subscribe({
      next: (products) => {
        this.products = products;
        this.isLoading = false;
      },
      error: (error: { error?: { message?: string } }) => this.handleError(error)
    });
  }

  hasSession(): boolean {
    return this.authService.hasSession();
  }

  logout(): void {
    this.authService.logout().subscribe({
      next: () => void this.router.navigate(['/auth/login']),
      error: () => {
        this.authService.clearSession();
        void this.router.navigate(['/auth/login']);
      }
    });
  }

  private loadProducts(): void {
    this.isLoading = true;
    this.catalogService.getProducts().subscribe({
      next: (products) => {
        this.products = products;
        this.setFilterOptions(products);
        this.isLoading = false;
      },
      error: (error: { error?: { message?: string } }) => this.handleError(error)
    });
  }

  private setFilterOptions(products: Producto[]): void {
    this.categorias = [...new Set(products.map((product) => product.categoria.nombre))].sort();
    this.tallas = [...new Set(products.flatMap((product) => product.variantes.map((variant) => variant.talla)))].sort();
    this.colores = [...new Set(products.flatMap((product) => product.variantes.map((variant) => variant.color)))].sort();
  }

  private handleError(error: { error?: { message?: string } }): void {
    this.isLoading = false;
    this.snackBar.open(error.error?.message ?? 'No fue posible cargar el catálogo', 'Cerrar', {
      duration: 5000
    });
  }
}

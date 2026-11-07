import { RecommendationsSectionComponent } from '../../../experience/recommendations-section.component';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { DatePipe } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Producto } from '../../../../shared/models/producto.model';
import { AuthService } from '../../../auth/services/auth.service';
import { ProductCardComponent } from '../../components/product-card/product-card.component';
import { ProductFilterComponent } from '../../components/product-filter/product-filter.component';
import { CatalogService, ProductSearchFilters } from '../../services/catalog.service';
import { PublicOrganizationContextService } from '../../services/public-organization-context.service';

@Component({
  selector: 'app-catalog-list',
  standalone: true,
  imports: [
    DatePipe,
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
  private readonly route = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly publicContext = inject(PublicOrganizationContextService);
  private readonly snackBar = inject(MatSnackBar);

  products: Producto[] = [];
  categorias: string[] = [];
  tallas: string[] = [];
  colores: string[] = [];
  isLoading = true;
  organizationSlug = '';
  hasCatalogContext = false;
  online = typeof navigator === 'undefined' || navigator.onLine;
  lastSync: number | null = null;

  ngOnInit(): void {
    window.addEventListener('online', this.connectionChanged);
    window.addEventListener('offline', this.connectionChanged);
    this.destroyRef.onDestroy(() => {
      window.removeEventListener('online', this.connectionChanged);
      window.removeEventListener('offline', this.connectionChanged);
    });
    this.organizationSlug = this.publicContext.publicSlug ?? '';
    this.route.queryParamMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.hasCatalogContext = this.catalogService.canLoadCatalog;
      if (this.hasCatalogContext) this.loadProducts();
      else {
        this.products = [];
        this.isLoading = false;
      }
    });
  }

  private readonly connectionChanged = (): void => {
    this.online = navigator.onLine;
    if (this.online && this.hasCatalogContext) this.loadProducts();
  };

  setOrganizationSlug(event: Event): void {
    event.preventDefault();
    const slug = PublicOrganizationContextService.validateSlug(this.organizationSlug);
    if (!slug) {
      this.snackBar.open('Ingresa un slug de tienda válido', 'Cerrar', { duration: 4000 });
      return;
    }
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { organization_slug: slug },
      queryParamsHandling: 'merge'
    });
  }

  onFiltersChange(filters: ProductSearchFilters): void {
    if (!this.hasCatalogContext) return;
    this.isLoading = true;
    if (Object.keys(filters).length === 0) {
      this.loadProducts();
      return;
    }

    this.catalogService.searchProducts(filters).subscribe({
      next: (products) => {
        this.products = products;
        if (this.catalogService.online !== false) this.lastSync = Date.now();
        else this.catalogService.getCachedProducts?.().subscribe(snapshot => this.lastSync = snapshot.syncedAt);
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
    this.catalogService.getCachedProducts?.().subscribe(snapshot => {
      this.products = snapshot.products;
      this.lastSync = snapshot.syncedAt;
      this.setFilterOptions(snapshot.products);
    });
    this.snackBar.open(error.error?.message ?? 'No fue posible cargar el catálogo', 'Cerrar', {
      duration: 5000
    });
  }
}

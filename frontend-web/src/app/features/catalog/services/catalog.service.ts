import { Injectable } from '@angular/core';
import { Observable, from, of, switchMap, tap, catchError } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { PublicOrganizationContextService } from './public-organization-context.service';
import { CatalogOfflineStore } from './catalog-offline.store';
import {
  Producto,
  ProductAvailabilityResponse,
  ProductVariantsResponse
} from '../../../shared/models/producto.model';

export interface ProductSearchFilters {
  nombre?: string;
  categoria?: string;
  talla?: string;
  color?: string;
  precio_max?: number;
}

@Injectable({ providedIn: 'root' })
export class CatalogService {
  constructor(
    private readonly api: ApiService,
    private readonly context: PublicOrganizationContextService,
    private readonly offline: CatalogOfflineStore
  ) {}

  get online(): boolean { return typeof navigator === 'undefined' || navigator.onLine; }
  get cacheKey(): string | null {
    if (!this.context.isAuthenticated) return this.context.publicSlug ? `slug:${this.context.publicSlug}` : null;
    return this.context.organizationId ? `org:${this.context.organizationId}` : null;
  }
  getCachedProducts(): Observable<{ products: Producto[]; syncedAt: number | null }> {
    const key = this.cacheKey;
    return key ? from(this.offline.get(key)).pipe(switchMap(value => of({ products: value?.products ?? [], syncedAt: value?.syncedAt ?? null }))) : of({ products: [], syncedAt: null });
  }

  get canLoadCatalog(): boolean {
    return this.context.canLoadCatalog;
  }

  private query(filters: object = {}): string {
    if (!this.context.isAuthenticated && !this.context.publicSlug) {
      throw new Error('Selecciona una tienda con organization_slug para consultar el catálogo.');
    }
    const params = new URLSearchParams();
    if (!this.context.isAuthenticated && this.context.publicSlug) {
      params.set('organization_slug', this.context.publicSlug);
    }
    for (const [key, value] of Object.entries(filters)) {
      if (value !== undefined && value !== '') params.set(key, String(value));
    }
    return params.toString();
  }

  getProducts(): Observable<Producto[]> {
    const key = this.cacheKey;
    if (!this.online) return this.getCachedProducts().pipe(switchMap(value => of(value.products)));
    return this.api.get<Producto[]>(`/api/catalog/products?${this.query()}`).pipe(tap(products => {
      if (key) void this.offline.put({ key, products, syncedAt: Date.now() });
    }), catchError(error => this.getCachedProducts().pipe(switchMap(value => value.products.length ? of(value.products) : (() => { throw error; })()))));
  }

  searchProducts(filters: ProductSearchFilters): Observable<Producto[]> {
    if (!this.online) return this.getCachedProducts().pipe(switchMap(({ products }) => of(products.filter(product =>
      (!filters.nombre || product.nombre.toLocaleLowerCase().includes(filters.nombre.toLocaleLowerCase())) &&
      (!filters.categoria || product.categoria.nombre === filters.categoria) &&
      (!filters.talla || product.variantes.some(variant => variant.talla === filters.talla)) &&
      (!filters.color || product.variantes.some(variant => variant.color === filters.color)) &&
      (!filters.precio_max || Number(product.precio_base) <= filters.precio_max)
    ))));
    return this.api.get<Producto[]>(`/api/catalog/products/search?${this.query(filters)}`);
  }

  getProductVariants(idProducto: number): Observable<ProductVariantsResponse> {
    return this.api.get<ProductVariantsResponse>(`/api/catalog/products/${idProducto}/variants?${this.query()}`);
  }

  getProductAvailability(idProducto: number): Observable<ProductAvailabilityResponse> {
    return this.api.get<ProductAvailabilityResponse>(`/api/catalog/products/${idProducto}/availability?${this.query()}`);
  }
}

import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
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
  constructor(private readonly api: ApiService) {}

  getProducts(): Observable<Producto[]> {
    return this.api.get<Producto[]>('/api/catalog/products');
  }

  searchProducts(filters: ProductSearchFilters): Observable<Producto[]> {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(filters)) {
      if (value !== undefined && value !== '') {
        params.set(key, String(value));
      }
    }
    const query = params.size > 0 ? `?${params.toString()}` : '';
    return this.api.get<Producto[]>(`/api/catalog/products/search${query}`);
  }

  getProductVariants(idProducto: number): Observable<ProductVariantsResponse> {
    return this.api.get<ProductVariantsResponse>(`/api/catalog/products/${idProducto}/variants`);
  }

  getProductAvailability(idProducto: number): Observable<ProductAvailabilityResponse> {
    return this.api.get<ProductAvailabilityResponse>(`/api/catalog/products/${idProducto}/availability`);
  }
}

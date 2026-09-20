import { Injectable } from '@angular/core';
import { Observable, map, throwError } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { AdminProduct, ProductRequest } from '../models/product-admin.model';

@Injectable({ providedIn: 'root' })
export class ProductAdminService {
  constructor(private readonly api: ApiService) {}
  list(): Observable<AdminProduct[]> { return this.api.get<AdminProduct[]>('/api/admin/products'); }
  getById(id: number): Observable<AdminProduct> { return this.list().pipe(map((products) => { const product = products.find((item) => item.id_producto === id); if (!product) throw new Error('Producto no encontrado'); return product; })); }
  create(request: ProductRequest): Observable<AdminProduct> { return this.api.post<AdminProduct>('/api/admin/products', request); }
  update(id: number, request: Partial<ProductRequest>): Observable<AdminProduct> { return this.api.put<AdminProduct>(`/api/admin/products/${id}`, request); }
  uploadImage(id: number, file: File): Observable<{ imagen_url: string }> {
    const formData = new FormData();
    formData.append('file', file);
    return this.api.post<{ imagen_url: string }>(`/api/admin/products/${id}/image`, formData);
  }
  deleteImage(id: number): Observable<void> { return this.api.delete<void>(`/api/admin/products/${id}/image`); }
  disable(id: number): Observable<AdminProduct> { return this.api.delete<AdminProduct>(`/api/admin/products/${id}`); }
}

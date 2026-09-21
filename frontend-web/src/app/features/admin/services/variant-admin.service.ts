import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { AdminVariant, VariantRequest } from '../models/variant-admin.model';

@Injectable({ providedIn: 'root' })
export class VariantAdminService {
  constructor(private readonly api: ApiService) {}
  list(productId: number): Observable<AdminVariant[]> { return this.api.get<AdminVariant[]>(`/api/admin/products/${productId}/variants`); }
  listAll(): Observable<AdminVariant[]> { return this.api.get<AdminVariant[]>('/api/admin/variants'); }
  create(productId: number, request: VariantRequest): Observable<AdminVariant> { return this.api.post<AdminVariant>(`/api/admin/products/${productId}/variants`, request); }
  update(id: number, request: Partial<VariantRequest>): Observable<AdminVariant> { return this.api.put<AdminVariant>(`/api/admin/variants/${id}`, request); }
  disable(id: number): Observable<AdminVariant> { return this.api.delete<AdminVariant>(`/api/admin/variants/${id}`); }
}

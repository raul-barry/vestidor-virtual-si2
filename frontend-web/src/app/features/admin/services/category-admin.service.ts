import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { AdminCategory } from '../models/category-admin.model';
@Injectable({ providedIn: 'root' })
export class CategoryAdminService {
  constructor(private readonly api: ApiService) {}
  list(): Observable<AdminCategory[]> { return this.api.get<AdminCategory[]>('/api/admin/categories'); }
  create(request: unknown): Observable<AdminCategory> { return this.api.post<AdminCategory>('/api/admin/categories', request); }
  update(id: number, request: unknown): Observable<AdminCategory> { return this.api.put<AdminCategory>(`/api/admin/categories/${id}`, request); }
  delete(id: number): Observable<void> { return this.api.delete<void>(`/api/admin/categories/${id}`); }
}

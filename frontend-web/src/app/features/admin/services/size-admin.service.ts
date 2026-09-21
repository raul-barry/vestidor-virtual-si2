import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { AdminSize } from '../models/size-admin.model';
@Injectable({ providedIn: 'root' })
export class SizeAdminService {
  constructor(private readonly api: ApiService) {}
  list(): Observable<AdminSize[]> { return this.api.get<AdminSize[]>('/api/admin/sizes'); }
  create(request: unknown): Observable<AdminSize> { return this.api.post<AdminSize>('/api/admin/sizes', request); }
  update(id: number, request: unknown): Observable<AdminSize> { return this.api.put<AdminSize>(`/api/admin/sizes/${id}`, request); }
  delete(id: number): Observable<void> { return this.api.delete<void>(`/api/admin/sizes/${id}`); }
}

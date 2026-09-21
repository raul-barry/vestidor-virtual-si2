import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { AdminColor } from '../models/color-admin.model';
@Injectable({ providedIn: 'root' })
export class ColorAdminService {
  constructor(private readonly api: ApiService) {}
  list(): Observable<AdminColor[]> { return this.api.get<AdminColor[]>('/api/admin/colors'); }
  create(request: unknown): Observable<AdminColor> { return this.api.post<AdminColor>('/api/admin/colors', request); }
  update(id: number, request: unknown): Observable<AdminColor> { return this.api.put<AdminColor>(`/api/admin/colors/${id}`, request); }
  delete(id: number): Observable<void> { return this.api.delete<void>(`/api/admin/colors/${id}`); }
}

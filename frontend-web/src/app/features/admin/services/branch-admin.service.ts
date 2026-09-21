import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { AdminBranch } from '../models/branch-admin.model';
@Injectable({ providedIn: 'root' })
export class BranchAdminService {
  constructor(private readonly api: ApiService) {}
  list(): Observable<AdminBranch[]> { return this.api.get<AdminBranch[]>('/api/admin/branches'); }
  create(request: unknown): Observable<AdminBranch> { return this.api.post<AdminBranch>('/api/admin/branches', request); }
  update(id: number, request: unknown): Observable<AdminBranch> { return this.api.put<AdminBranch>(`/api/admin/branches/${id}`, request); }
  toggleStatus(id: number): Observable<AdminBranch> { return this.api.patch<AdminBranch>(`/api/admin/branches/${id}/toggle-status`, {}); }
  delete(id: number): Observable<void> { return this.api.delete<void>(`/api/admin/branches/${id}`); }
}

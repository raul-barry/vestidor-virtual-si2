import { Injectable } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { CreateUserAdminRequest, UpdateUserRoleRequest, UpdateUserStatusRequest, UserAdmin } from '../models/user-admin.model';

@Injectable({ providedIn: 'root' })
export class UserAdminService {
  constructor(private api: ApiService) {}
  getUsers(filters?: { rol?: string; estado?: string; search?: string }): Observable<UserAdmin[]> {
    return this.api.get<UserAdmin[]>('/api/admin/users').pipe(
      map((users) => users.filter((user) =>
        (!filters?.rol || user.rol === filters.rol) &&
        (!filters?.estado || user.estado === filters.estado) &&
        (!filters?.search || `${user.nombres} ${user.apellidos} ${user.correo}`.toLowerCase().includes(filters.search.toLowerCase()))
      ))
    );
  }
  getUserDetail(id: number): Observable<UserAdmin> { return this.api.get<UserAdmin>(`/api/admin/users/${id}`); }
  createUser(data: CreateUserAdminRequest): Observable<UserAdmin> { return this.api.post<UserAdmin>('/api/admin/users', data); }
  updateStatus(id: number, data: UpdateUserStatusRequest): Observable<UserAdmin> { return this.api.put<UserAdmin>(`/api/admin/users/${id}/status`, data); }
  updateRole(id: number, data: UpdateUserRoleRequest): Observable<UserAdmin> { return this.api.put<UserAdmin>(`/api/admin/users/${id}/role`, data); }
}

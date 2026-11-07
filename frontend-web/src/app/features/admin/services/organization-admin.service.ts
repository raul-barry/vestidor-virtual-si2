import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { CreateOrganizationRequest, OrganizationAdmin, OrganizationAdminRequest, OrganizationBranchAdmin, OrganizationUserAdmin, TenantProvisionRequest, TenantProvisionResult, UpdateOrganizationRequest } from '../models/organization-admin.model';

@Injectable({ providedIn: 'root' })
export class OrganizationAdminService {
  private readonly base = '/api/platform/organizations';

  constructor(private readonly api: ApiService) {}

  list(): Observable<OrganizationAdmin[]> {
    return this.api.get<OrganizationAdmin[]>(this.base);
  }

  get(id: number): Observable<OrganizationAdmin> {
    return this.api.get<OrganizationAdmin>(`${this.base}/${id}`);
  }

  listBranches(id: number): Observable<OrganizationBranchAdmin[]> {
    return this.api.get<OrganizationBranchAdmin[]>(`${this.base}/${id}/branches`);
  }

  listUsers(id: number): Observable<OrganizationUserAdmin[]> {
    return this.api.get<OrganizationUserAdmin[]>(`${this.base}/${id}/users`);
  }

  create(request: CreateOrganizationRequest): Observable<OrganizationAdmin> {
    return this.api.post<OrganizationAdmin>(this.base, request);
  }

  provision(request: TenantProvisionRequest): Observable<TenantProvisionResult> {
    return this.api.post<TenantProvisionResult>(`${this.base}/provision`, request);
  }

  update(id: number, request: UpdateOrganizationRequest): Observable<OrganizationAdmin> {
    return this.api.patch<OrganizationAdmin>(`${this.base}/${id}`, request);
  }

  updateStatus(id: number, estado: OrganizationAdmin['estado']): Observable<OrganizationAdmin> {
    return this.api.patch<OrganizationAdmin>(`${this.base}/${id}/status`, { estado });
  }

  createFirstAdministrator(id: number, request: OrganizationAdminRequest): Observable<{ id_usuario: number; id_organizacion: number; correo: string; rol: string }> {
    return this.api.post(`${this.base}/${id}/administrators`, request);
  }
}
